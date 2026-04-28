use std::io::{Read, Seek, SeekFrom};
use std::path::Path;

use crate::pricing::PricingTable;

pub struct ScanResult {
    pub session_id: String,
    pub cost_delta: f64,
    pub input_delta: u64,
    pub output_delta: u64,
    pub cache_read_delta: u64,
    pub cache_write_delta: u64,
    pub new_offset: u64,
    pub is_complete: bool,
}

/// Incrementally scan one events.jsonl file from `last_offset`.
///
/// Offset correctness invariant:
///   `data.split(b'\n')` always yields N slices for N-1 `\n` characters.
///   The last slice is either empty (file ends with `\n`, all lines complete)
///   or non-empty (partial last line still being written — skip it).
///   In both cases `complete_slices = &slices[..slices.len()-1]` gives
///   exactly the set of fully-terminated lines.  `bytes_consumed` advances
///   `new_offset` only past those lines and their newlines.
pub fn scan_file(
    session_id: &str,
    path: &Path,
    last_offset: u64,
    pricing: &PricingTable,
) -> Option<ScanResult> {
    let mut file = std::fs::File::open(path).ok()?;

    // Fast skip: nothing new to read
    let file_size = file.metadata().ok()?.len();
    if file_size <= last_offset {
        return None;
    }

    file.seek(SeekFrom::Start(last_offset)).ok()?;
    let mut data = Vec::with_capacity((file_size - last_offset) as usize);
    file.read_to_end(&mut data).ok()?;
    if data.is_empty() {
        return None;
    }

    // Split on '\n'.  Last element = empty (clean end) or partial write.
    // Either way slices[..len-1] are the fully-terminated lines.
    let slices: Vec<&[u8]> = data.split(|&b| b == b'\n').collect();
    let complete_slices = &slices[..slices.len().saturating_sub(1)];

    // Bytes consumed = every complete line + its '\n'
    let bytes_consumed: usize = complete_slices.iter().map(|s| s.len() + 1).sum();
    if bytes_consumed == 0 {
        return None; // Only a partial line at EOF — nothing ready to process
    }

    let mut cost_delta = 0.0f64;
    let mut input_delta = 0u64;
    let mut output_delta = 0u64;
    let mut cache_read_delta = 0u64;
    let mut cache_write_delta = 0u64;
    let mut is_complete = false;

    for &slice in complete_slices {
        let line = trim_ascii(slice);
        if line.is_empty() {
            continue;
        }
        // Cheap pre-filter — avoids JSON parsing for the majority of events
        let has_llm = memmem(line, b"\"llm:response\"");
        let has_end = memmem(line, b"\"session:end\"");
        if !has_llm && !has_end {
            continue;
        }

        let v: serde_json::Value = match serde_json::from_slice(line) {
            Ok(v) => v,
            Err(_) => continue,
        };
        match v.get("event").and_then(|e| e.as_str()).unwrap_or("") {
            "llm:response" => {
                let data_obj = &v["data"];
                let usage = &data_obj["usage"];
                let model = data_obj
                    .get("model")
                    .and_then(|m| m.as_str())
                    .unwrap_or("");
                let inp = tok(usage, &["input_tokens", "input"]);
                let out = tok(usage, &["output_tokens", "output"]);
                let cr = tok(usage, &["cache_read_tokens", "cache_read"]);
                let cw = tok(usage, &["cache_write_tokens", "cache_write"]);
                cost_delta += pricing.compute_cost(model, inp, out, cr, cw);
                input_delta += inp;
                output_delta += out;
                cache_read_delta += cr;
                cache_write_delta += cw;
            }
            "session:end" => {
                is_complete = true;
            }
            _ => {}
        }
    }

    Some(ScanResult {
        session_id: session_id.to_string(),
        cost_delta,
        input_delta,
        output_delta,
        cache_read_delta,
        cache_write_delta,
        new_offset: last_offset + bytes_consumed as u64,
        is_complete,
    })
}

// ── tiny helpers (no external deps) ──────────────────────────────────────────

fn memmem(haystack: &[u8], needle: &[u8]) -> bool {
    haystack.windows(needle.len()).any(|w| w == needle)
}

fn trim_ascii(s: &[u8]) -> &[u8] {
    let start = s.iter().position(|&b| b > b' ').unwrap_or(s.len());
    let end = s.iter().rposition(|&b| b > b' ').map(|i| i + 1).unwrap_or(0);
    if start < end {
        &s[start..end]
    } else {
        &[]
    }
}

fn tok(obj: &serde_json::Value, keys: &[&str]) -> u64 {
    for k in keys {
        if let Some(v) = obj.get(k).and_then(|v| v.as_u64()) {
            return v;
        }
    }
    0
}
