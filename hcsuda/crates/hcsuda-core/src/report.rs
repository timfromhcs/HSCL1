//! Benchmark evidence rows. One JSON file per device, written by the CLI.
//!
//! Every number carries its own context: device, driver, dtype, shape, path and
//! repetition count. A number without context is not evidence.

use serde::{Deserialize, Serialize};

use crate::SCHEMA_VERSION;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BenchRow {
    pub schema: u32,
    pub op: String,
    pub dtype: String,
    pub shape: [usize; 3],
    pub path: String,
    pub device: String,
    pub driver: String,
    pub runs: u32,
    pub median_ms: f64,
    pub min_ms: f64,
    pub max_ms: f64,
    /// Median GPU-side time from timestamp queries, when the device reports them.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub gpu_median_ms: Option<f64>,
    /// Relative spread of the GPU-side samples, when available.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub gpu_spread: Option<f64>,
    pub gflops: Option<f64>,
    pub gbps: Option<f64>,
    pub bytes_moved: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub note: Option<String>,
}

impl BenchRow {
    /// Build a row from wall-clock samples (milliseconds). `flops` and
    /// `bytes_moved` are the theoretical work of one run, used for the rates.
    ///
    /// Nine arguments is deliberate: this is the evidence constructor, and every
    /// field must be supplied explicitly rather than defaulted.
    #[allow(clippy::too_many_arguments)]
    pub fn from_samples(
        op: &str,
        dtype: &str,
        shape: [usize; 3],
        path: &str,
        device: &str,
        driver: &str,
        mut samples_ms: Vec<f64>,
        flops: Option<f64>,
        bytes_moved: Option<u64>,
    ) -> Self {
        assert!(
            !samples_ms.is_empty(),
            "a benchmark row needs at least one sample"
        );
        samples_ms.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        let median_ms = median(&samples_ms);
        let min_ms = *samples_ms.first().unwrap();
        let max_ms = *samples_ms.last().unwrap();
        let seconds = median_ms / 1000.0;
        let gflops = flops
            .filter(|f| *f > 0.0 && seconds > 0.0)
            .map(|f| f / seconds / 1e9);
        let gbps = bytes_moved
            .filter(|b| *b > 0 && seconds > 0.0)
            .map(|b| b as f64 / seconds / 1e9);
        Self {
            schema: SCHEMA_VERSION,
            op: op.to_string(),
            dtype: dtype.to_string(),
            shape,
            path: path.to_string(),
            device: device.to_string(),
            driver: driver.to_string(),
            runs: samples_ms.len() as u32,
            median_ms,
            min_ms,
            max_ms,
            gpu_median_ms: None,
            gpu_spread: None,
            gflops,
            gbps,
            bytes_moved,
            note: None,
        }
    }

    /// Spread as a fraction of the median; the gate refuses > 0.25 (noisy).
    pub fn spread(&self) -> f64 {
        if self.median_ms <= 0.0 {
            return 0.0;
        }
        (self.max_ms - self.min_ms) / self.median_ms
    }

    pub fn with_note(mut self, note: impl Into<String>) -> Self {
        self.note = Some(note.into());
        self
    }

    pub fn with_gpu_median(mut self, gpu_median_ms: Option<f64>) -> Self {
        self.gpu_median_ms = gpu_median_ms;
        self
    }

    /// Attach GPU-side statistics: `(median_ms, relative_spread)`.
    pub fn with_gpu_stats(mut self, stats: Option<(f64, f64)>) -> Self {
        if let Some((median_ms, spread)) = stats {
            self.gpu_median_ms = Some(median_ms);
            self.gpu_spread = Some(spread);
        }
        self
    }

    /// Spread of a sample set, relative to its median.
    pub fn spread_of(mut samples: Vec<f64>) -> Option<f64> {
        if samples.len() < 2 {
            return None;
        }
        samples.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        let median = median(&samples);
        if median <= 0.0 {
            return None;
        }
        let min = *samples.first()?;
        let max = *samples.last()?;
        Some((max - min) / median)
    }

    /// Median of unsorted samples, or `None` for an empty slice.
    pub fn median_of(mut samples: Vec<f64>) -> Option<f64> {
        if samples.is_empty() {
            return None;
        }
        samples.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        Some(median(&samples))
    }
}

fn median(sorted: &[f64]) -> f64 {
    let n = sorted.len();
    if n % 2 == 1 {
        sorted[n / 2]
    } else {
        (sorted[n / 2 - 1] + sorted[n / 2]) / 2.0
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BenchSuite {
    pub schema: u32,
    pub device: String,
    pub driver: String,
    pub rows: Vec<BenchRow>,
}

impl BenchSuite {
    pub fn new(device: impl Into<String>, driver: impl Into<String>) -> Self {
        Self {
            schema: SCHEMA_VERSION,
            device: device.into(),
            driver: driver.into(),
            rows: Vec::new(),
        }
    }

    pub fn push(&mut self, row: BenchRow) {
        self.rows.push(row);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn median_of_odd_and_even_counts() {
        assert_eq!(median(&[1.0, 2.0, 3.0]), 2.0);
        assert_eq!(median(&[1.0, 2.0, 3.0, 4.0]), 2.5);
    }

    #[test]
    fn rates_are_derived_from_the_median() {
        // 2 GFLOP in 1000 ms = 2 GFLOP/s
        let row = BenchRow::from_samples(
            "gemm",
            "f32",
            [64, 64, 64],
            "reference",
            "cpu",
            "none",
            vec![1000.0],
            Some(2e9),
            Some(4_000_000_000),
        );
        assert!((row.gflops.unwrap() - 2.0).abs() < 1e-9);
        assert!((row.gbps.unwrap() - 4.0).abs() < 1e-9);
        assert_eq!(row.spread(), 0.0);
    }

    #[test]
    fn spread_reflects_noise() {
        let row = BenchRow::from_samples(
            "saxpy",
            "f32",
            [1024, 0, 0],
            "reference",
            "cpu",
            "none",
            vec![10.0, 20.0],
            None,
            None,
        );
        // median 15, range 10 -> 2/3
        assert!((row.spread() - 2.0 / 3.0).abs() < 1e-9);
        assert!(row.gflops.is_none());
    }
}
