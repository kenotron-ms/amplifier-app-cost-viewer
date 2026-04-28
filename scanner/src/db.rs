use rusqlite::{params, Connection, Result};
use std::collections::HashMap;
use std::path::Path;

use crate::scan::ScanResult;

const SCHEMA: &str = "
PRAGMA journal_mode = WAL;
PRAGMA synchronous  = NORMAL;

CREATE TABLE IF NOT EXISTS session_summaries (
    session_id    TEXT    PRIMARY KEY,
    cost_usd      REAL    NOT NULL DEFAULT 0.0,
    input_tokens  INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cache_read    INTEGER NOT NULL DEFAULT 0,
    cache_write   INTEGER NOT NULL DEFAULT 0,
    last_offset   INTEGER NOT NULL DEFAULT 0,
    is_complete   INTEGER NOT NULL DEFAULT 0,
    updated_at    REAL    NOT NULL DEFAULT 0.0
);
";

pub fn open(path: &Path) -> Result<Connection> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).ok();
    }
    let conn = Connection::open(path)?;
    conn.execute_batch(SCHEMA)?;
    Ok(conn)
}

/// Bulk-read all existing (last_offset, is_complete) rows in one pass.
/// Returns a HashMap so callers can skip complete sessions before touching the filesystem.
pub fn load_states(conn: &Connection) -> Result<HashMap<String, (u64, bool)>> {
    let mut stmt = conn.prepare(
        "SELECT session_id, last_offset, is_complete FROM session_summaries",
    )?;
    let rows = stmt.query_map([], |row| {
        Ok((
            row.get::<_, String>(0)?,
            row.get::<_, i64>(1)? as u64,
            row.get::<_, i64>(2)? != 0,
        ))
    })?;
    let mut map = HashMap::new();
    for row in rows.flatten() {
        map.insert(row.0, (row.1, row.2));
    }
    Ok(map)
}

/// Batch-upsert scan results in a single transaction.
///
/// Cost/token fields are *added* to existing values so incremental deltas
/// accumulate correctly.  `last_offset` and `is_complete` are replaced.
pub fn upsert_batch(conn: &mut Connection, results: &[ScanResult]) -> Result<()> {
    if results.is_empty() {
        return Ok(());
    }
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs_f64();

    let tx = conn.transaction()?;
    {
        let mut stmt = tx.prepare_cached(
            "INSERT INTO session_summaries
                 (session_id, cost_usd, input_tokens, output_tokens,
                  cache_read, cache_write, last_offset, is_complete, updated_at)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)
             ON CONFLICT(session_id) DO UPDATE SET
                 cost_usd      = cost_usd      + excluded.cost_usd,
                 input_tokens  = input_tokens  + excluded.input_tokens,
                 output_tokens = output_tokens + excluded.output_tokens,
                 cache_read    = cache_read    + excluded.cache_read,
                 cache_write   = cache_write   + excluded.cache_write,
                 last_offset   = excluded.last_offset,
                 is_complete   = MAX(is_complete, excluded.is_complete),
                 updated_at    = excluded.updated_at",
        )?;
        for r in results {
            stmt.execute(params![
                r.session_id,
                r.cost_delta,
                r.input_delta as i64,
                r.output_delta as i64,
                r.cache_read_delta as i64,
                r.cache_write_delta as i64,
                r.new_offset as i64,
                i64::from(r.is_complete),
                now,
            ])?;
        }
    }
    tx.commit()
}
