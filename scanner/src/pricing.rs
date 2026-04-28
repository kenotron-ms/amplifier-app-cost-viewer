use serde::Deserialize;
use std::collections::HashMap;
use std::path::Path;

/// Raw shape from Python's STATIC_PRICING dict.
#[derive(Deserialize)]
struct RawEntry {
    #[serde(default)]
    input_cost_per_token: f64,
    #[serde(default)]
    output_cost_per_token: f64,
    #[serde(default)]
    cache_read_input_token_cost: f64,
    #[serde(default)]
    cache_creation_input_token_cost: f64,
}

struct Entry {
    input: f64,
    output: f64,
    cache_read: f64,
    cache_write: f64,
}

/// Pricing lookup table loaded from the Python-generated pricing.json.
pub struct PricingTable {
    entries: HashMap<String, Entry>,
}

impl PricingTable {
    /// Load from a JSON file.  Returns an empty table if the file is absent
    /// or malformed — costs will show as 0.0 for unknown models.
    pub fn load(path: &Path) -> Self {
        let entries = std::fs::read_to_string(path)
            .ok()
            .and_then(|s| serde_json::from_str::<HashMap<String, RawEntry>>(&s).ok())
            .map(|raw| {
                raw.into_iter()
                    .map(|(model, r)| {
                        (
                            model,
                            Entry {
                                input: r.input_cost_per_token,
                                output: r.output_cost_per_token,
                                cache_read: r.cache_read_input_token_cost,
                                cache_write: r.cache_creation_input_token_cost,
                            },
                        )
                    })
                    .collect()
            })
            .unwrap_or_default();

        Self { entries }
    }

    /// Cost for one LLM call, in USD.
    /// Tries exact match, then longest prefix match.
    pub fn compute_cost(
        &self,
        model: &str,
        input_tokens: u64,
        output_tokens: u64,
        cache_read: u64,
        cache_write: u64,
    ) -> f64 {
        match self.find(model) {
            Some(e) => {
                e.input * input_tokens as f64
                    + e.output * output_tokens as f64
                    + e.cache_read * cache_read as f64
                    + e.cache_write * cache_write as f64
            }
            None => 0.0,
        }
    }

    fn find(&self, model: &str) -> Option<&Entry> {
        if let Some(e) = self.entries.get(model) {
            return Some(e);
        }
        // Longest-prefix fallback (e.g. table has "claude-3-5-sonnet",
        // model is "claude-3-5-sonnet-20241022")
        self.entries
            .iter()
            .filter(|(k, _)| model.starts_with(k.as_str()))
            .max_by_key(|(k, _)| k.len())
            .map(|(_, v)| v)
    }
}
