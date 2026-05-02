"""Offline A/B test simulation for Final Project Component 2.

The experiment compares two RAG variants:

- Control A: current Milestone 6 RAG configuration, top_k=5.
- Treatment B: narrower-context RAG configuration, top_k=3.

The script is intentionally self-contained. It does not call the local API,
Ollama, FAISS, or external A/B testing platforms. Running it generates synthetic
traffic, evaluates primary and guardrail metrics, and writes reproducible
artifacts under ``docs/``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs"


@dataclass(frozen=True)
class VariantConfig:
    """Synthetic outcome assumptions for one RAG variant."""

    name: str
    label: str
    top_k: int
    success_rate: float
    latency_mean_ms: float
    latency_sd_ms: float
    groundedness_mean: float
    groundedness_sd: float
    recall_mean: float
    recall_sd: float
    error_rate: float
    business_value_mean: float
    business_value_sd: float


@dataclass(frozen=True)
class ExperimentConfig:
    """Experiment design parameters."""

    experiment_name: str = "rag_topk_context_ab_test"
    total_users: int = 20_000
    traffic_split_control: float = 0.50
    alpha: float = 0.05
    power: float = 0.80
    minimum_detectable_effect: float = 0.05
    max_recall_degradation: float = 0.05
    max_error_rate_increase: float = 0.005
    max_latency_degradation: float = 0.00
    seed: int = 568


@dataclass(frozen=True)
class Observation:
    """One synthetic user/request outcome."""

    user_id: str
    variant: str
    query_type: str
    success: bool
    latency_ms: float
    groundedness_score: float
    recall_proxy: float
    error: bool
    business_value: float


@dataclass(frozen=True)
class TestResult:
    """Result of one statistical comparison."""

    metric_name: str
    test_type: str
    control_value: float
    treatment_value: float
    difference: float
    relative_lift: float
    statistic: float
    p_value: float
    ci_lower: float
    ci_upper: float
    significant: bool


@dataclass(frozen=True)
class GuardrailResult:
    """Pass/fail result for a launch guardrail."""

    metric_name: str
    control_value: float
    treatment_value: float
    threshold: float
    passed: bool
    reason: str


CONTROL = VariantConfig(
    name="control",
    label="A: baseline RAG top_k=5",
    top_k=5,
    success_rate=0.72,
    latency_mean_ms=2914.23,
    latency_sd_ms=650.0,
    groundedness_mean=0.78,
    groundedness_sd=0.08,
    recall_mean=1.00,
    recall_sd=0.015,
    error_rate=0.010,
    business_value_mean=1.00,
    business_value_sd=0.22,
)

TREATMENT = VariantConfig(
    name="treatment",
    label="B: narrower RAG top_k=3",
    top_k=3,
    success_rate=0.77,
    latency_mean_ms=2400.0,
    latency_sd_ms=560.0,
    groundedness_mean=0.82,
    groundedness_sd=0.07,
    recall_mean=0.96,
    recall_sd=0.03,
    error_rate=0.011,
    business_value_mean=1.07,
    business_value_sd=0.23,
)

QUERY_TYPES = (
    "rag_definition",
    "grounding_hallucination",
    "chunking_settings",
    "local_llm_serving",
    "agent_components",
    "personalization_bias",
)


def normal_cdf(value: float) -> float:
    """Standard normal cumulative distribution function."""

    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def inverse_normal_cdf(probability: float) -> float:
    """Acklam approximation for the standard normal quantile function."""

    if probability <= 0.0 or probability >= 1.0:
        raise ValueError("probability must be between 0 and 1")

    a = (
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    )
    b = (
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    )
    c = (
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    )
    d = (
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    )

    lower = 0.02425
    upper = 1.0 - lower

    if probability < lower:
        q = math.sqrt(-2.0 * math.log(probability))
        return (
            (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
            / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
        )
    if probability > upper:
        q = math.sqrt(-2.0 * math.log(1.0 - probability))
        return -(
            (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
            / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
        )

    q = probability - 0.5
    r = q * q
    return (
        (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q
        / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    )


def calculate_sample_size(
    baseline_rate: float,
    minimum_detectable_effect: float,
    alpha: float,
    power: float,
) -> int:
    """Approximate required sample size per variant for a two-sided proportion test."""

    p1 = baseline_rate
    p2 = baseline_rate * (1.0 + minimum_detectable_effect)
    effect_size = abs(2.0 * (math.asin(math.sqrt(p2)) - math.asin(math.sqrt(p1))))
    if effect_size == 0.0:
        raise ValueError("minimum_detectable_effect must produce a non-zero effect size")

    z_alpha = inverse_normal_cdf(1.0 - alpha / 2.0)
    z_power = inverse_normal_cdf(power)
    return math.ceil(2.0 * ((z_alpha + z_power) / effect_size) ** 2)


def assign_variant(user_id: str, experiment_name: str, control_weight: float) -> str:
    """Assign a user deterministically using consistent hashing."""

    hash_input = f"{user_id}:{experiment_name}".encode("utf-8")
    hash_value = hashlib.md5(hash_input).hexdigest()
    bucket = int(hash_value[:8], 16) / float(16**8)
    return CONTROL.name if bucket < control_weight else TREATMENT.name


def clipped_gaussian(rng: random.Random, mean: float, sd: float, low: float, high: float) -> float:
    """Sample a Gaussian value and clamp it to a valid metric range."""

    return max(low, min(high, rng.gauss(mean, sd)))


def variant_for_name(name: str) -> VariantConfig:
    """Return the configured variant by internal name."""

    if name == CONTROL.name:
        return CONTROL
    if name == TREATMENT.name:
        return TREATMENT
    raise ValueError(f"unknown variant: {name}")


def simulate_experiment(config: ExperimentConfig) -> list[Observation]:
    """Generate deterministic synthetic traffic for the A/B experiment."""

    rng = random.Random(config.seed)
    observations: list[Observation] = []

    for index in range(config.total_users):
        user_id = f"user_{index:06d}"
        variant_name = assign_variant(
            user_id=user_id,
            experiment_name=config.experiment_name,
            control_weight=config.traffic_split_control,
        )
        variant = variant_for_name(variant_name)
        query_type = QUERY_TYPES[index % len(QUERY_TYPES)]
        error = rng.random() < variant.error_rate
        success = (not error) and (rng.random() < variant.success_rate)
        latency_ms = clipped_gaussian(
            rng,
            mean=variant.latency_mean_ms,
            sd=variant.latency_sd_ms,
            low=250.0,
            high=8_000.0,
        )
        groundedness = clipped_gaussian(
            rng,
            mean=variant.groundedness_mean,
            sd=variant.groundedness_sd,
            low=0.0,
            high=1.0,
        )
        recall = clipped_gaussian(
            rng,
            mean=variant.recall_mean,
            sd=variant.recall_sd,
            low=0.0,
            high=1.0,
        )
        business_value = clipped_gaussian(
            rng,
            mean=variant.business_value_mean,
            sd=variant.business_value_sd,
            low=0.0,
            high=3.0,
        )

        observations.append(
            Observation(
                user_id=user_id,
                variant=variant_name,
                query_type=query_type,
                success=success,
                latency_ms=latency_ms,
                groundedness_score=groundedness,
                recall_proxy=recall,
                error=error,
                business_value=business_value,
            )
        )

    return observations


def split_by_variant(observations: Iterable[Observation]) -> dict[str, list[Observation]]:
    """Group observations by variant."""

    grouped = {CONTROL.name: [], TREATMENT.name: []}
    for observation in observations:
        grouped[observation.variant].append(observation)
    return grouped


def mean(values: list[float]) -> float:
    """Return the arithmetic mean or 0.0 for an empty list."""

    return statistics.fmean(values) if values else 0.0


def proportion_ztest(
    control_successes: int,
    control_n: int,
    treatment_successes: int,
    treatment_n: int,
    alpha: float,
    metric_name: str,
) -> TestResult:
    """Two-proportion z-test for the primary binary metric."""

    control_rate = control_successes / control_n
    treatment_rate = treatment_successes / treatment_n
    pooled = (control_successes + treatment_successes) / (control_n + treatment_n)
    se_pooled = math.sqrt(pooled * (1.0 - pooled) * (1.0 / control_n + 1.0 / treatment_n))
    diff = treatment_rate - control_rate
    z_stat = diff / se_pooled if se_pooled > 0.0 else 0.0
    p_value = 2.0 * (1.0 - normal_cdf(abs(z_stat)))

    se_diff = math.sqrt(
        control_rate * (1.0 - control_rate) / control_n
        + treatment_rate * (1.0 - treatment_rate) / treatment_n
    )
    z_crit = inverse_normal_cdf(1.0 - alpha / 2.0)
    ci_lower = diff - z_crit * se_diff
    ci_upper = diff + z_crit * se_diff

    return TestResult(
        metric_name=metric_name,
        test_type="two_proportion_ztest",
        control_value=control_rate,
        treatment_value=treatment_rate,
        difference=diff,
        relative_lift=diff / control_rate if control_rate > 0.0 else 0.0,
        statistic=z_stat,
        p_value=p_value,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        significant=p_value < alpha,
    )


def welch_ttest(
    control_values: list[float],
    treatment_values: list[float],
    alpha: float,
    metric_name: str,
) -> TestResult:
    """Welch-style normal approximation for comparing continuous metrics."""

    control_mean = mean(control_values)
    treatment_mean = mean(treatment_values)
    diff = treatment_mean - control_mean

    control_var = statistics.variance(control_values) if len(control_values) > 1 else 0.0
    treatment_var = statistics.variance(treatment_values) if len(treatment_values) > 1 else 0.0
    se = math.sqrt(control_var / len(control_values) + treatment_var / len(treatment_values))
    statistic = diff / se if se > 0.0 else 0.0
    p_value = 2.0 * (1.0 - normal_cdf(abs(statistic)))
    z_crit = inverse_normal_cdf(1.0 - alpha / 2.0)

    return TestResult(
        metric_name=metric_name,
        test_type="welch_ttest_normal_approx",
        control_value=control_mean,
        treatment_value=treatment_mean,
        difference=diff,
        relative_lift=diff / control_mean if control_mean else 0.0,
        statistic=statistic,
        p_value=p_value,
        ci_lower=diff - z_crit * se,
        ci_upper=diff + z_crit * se,
        significant=p_value < alpha,
    )


def percentile(values: list[float], quantile: float) -> float:
    """Nearest-rank percentile for summary reporting."""

    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = min(len(sorted_values) - 1, max(0, math.ceil(len(sorted_values) * quantile) - 1))
    return sorted_values[index]


def summarize_variant(observations: list[Observation]) -> dict[str, float | int]:
    """Compute per-variant descriptive statistics."""

    latencies = [row.latency_ms for row in observations]
    groundedness = [row.groundedness_score for row in observations]
    recalls = [row.recall_proxy for row in observations]
    business_values = [row.business_value for row in observations]
    successes = sum(1 for row in observations if row.success)
    errors = sum(1 for row in observations if row.error)
    n = len(observations)

    return {
        "n": n,
        "successes": successes,
        "success_rate": successes / n,
        "errors": errors,
        "error_rate": errors / n,
        "avg_latency_ms": mean(latencies),
        "p95_latency_ms": percentile(latencies, 0.95),
        "avg_groundedness_score": mean(groundedness),
        "avg_recall_proxy": mean(recalls),
        "avg_business_value": mean(business_values),
    }


def check_guardrails(
    control_summary: dict[str, float | int],
    treatment_summary: dict[str, float | int],
    config: ExperimentConfig,
) -> list[GuardrailResult]:
    """Evaluate launch guardrails."""

    recall_control = float(control_summary["avg_recall_proxy"])
    recall_treatment = float(treatment_summary["avg_recall_proxy"])
    recall_degradation = (recall_control - recall_treatment) / recall_control

    error_control = float(control_summary["error_rate"])
    error_treatment = float(treatment_summary["error_rate"])
    error_increase = error_treatment - error_control

    p95_control = float(control_summary["p95_latency_ms"])
    p95_treatment = float(treatment_summary["p95_latency_ms"])
    p95_change = (p95_treatment - p95_control) / p95_control

    return [
        GuardrailResult(
            metric_name="recall_proxy",
            control_value=recall_control,
            treatment_value=recall_treatment,
            threshold=config.max_recall_degradation,
            passed=recall_degradation <= config.max_recall_degradation,
            reason=f"relative degradation={recall_degradation:.2%}",
        ),
        GuardrailResult(
            metric_name="error_rate",
            control_value=error_control,
            treatment_value=error_treatment,
            threshold=config.max_error_rate_increase,
            passed=error_increase <= config.max_error_rate_increase,
            reason=f"absolute increase={error_increase:.4f}",
        ),
        GuardrailResult(
            metric_name="p95_latency_ms",
            control_value=p95_control,
            treatment_value=p95_treatment,
            threshold=config.max_latency_degradation,
            passed=p95_change <= config.max_latency_degradation,
            reason=f"relative change={p95_change:.2%}",
        ),
    ]


def make_recommendation(primary: TestResult, guardrails: list[GuardrailResult]) -> str:
    """Return the final ship decision."""

    guardrails_passed = all(result.passed for result in guardrails)
    if primary.significant and primary.difference > 0.0 and primary.ci_lower > 0.0 and guardrails_passed:
        return "SHIP_TREATMENT_GRADUALLY"
    if primary.significant and primary.difference < 0.0:
        return "KEEP_CONTROL"
    if not guardrails_passed:
        return "DO_NOT_SHIP_GUARDRAIL_FAILURE"
    return "RUN_MORE_DATA"


def analyze_experiment(observations: list[Observation], config: ExperimentConfig) -> dict[str, object]:
    """Run statistical tests and guardrail checks."""

    grouped = split_by_variant(observations)
    control_rows = grouped[CONTROL.name]
    treatment_rows = grouped[TREATMENT.name]
    control_summary = summarize_variant(control_rows)
    treatment_summary = summarize_variant(treatment_rows)

    primary = proportion_ztest(
        control_successes=int(control_summary["successes"]),
        control_n=int(control_summary["n"]),
        treatment_successes=int(treatment_summary["successes"]),
        treatment_n=int(treatment_summary["n"]),
        alpha=config.alpha,
        metric_name="successful_answer_rate",
    )
    tests = [
        primary,
        welch_ttest(
            [row.latency_ms for row in control_rows],
            [row.latency_ms for row in treatment_rows],
            alpha=config.alpha,
            metric_name="latency_ms",
        ),
        welch_ttest(
            [row.groundedness_score for row in control_rows],
            [row.groundedness_score for row in treatment_rows],
            alpha=config.alpha,
            metric_name="groundedness_score",
        ),
        welch_ttest(
            [row.business_value for row in control_rows],
            [row.business_value for row in treatment_rows],
            alpha=config.alpha,
            metric_name="business_value",
        ),
    ]
    guardrails = check_guardrails(control_summary, treatment_summary, config)
    recommendation = make_recommendation(primary, guardrails)

    return {
        "experiment": {
            **asdict(config),
            "control": asdict(CONTROL),
            "treatment": asdict(TREATMENT),
            "required_sample_size_per_variant": calculate_sample_size(
                baseline_rate=CONTROL.success_rate,
                minimum_detectable_effect=config.minimum_detectable_effect,
                alpha=config.alpha,
                power=config.power,
            ),
        },
        "summary": {
            CONTROL.name: control_summary,
            TREATMENT.name: treatment_summary,
        },
        "statistical_tests": [asdict(result) for result in tests],
        "guardrails": [asdict(result) for result in guardrails],
        "recommendation": recommendation,
    }


def write_markdown_summary(report: dict[str, object], output_path: Path) -> None:
    """Write a compact human-readable summary for the recommendation memo."""

    experiment = report["experiment"]
    summary = report["summary"]
    tests = report["statistical_tests"]
    guardrails = report["guardrails"]

    control = summary[CONTROL.name]
    treatment = summary[TREATMENT.name]
    primary = tests[0]

    lines = [
        "# Component 2 A/B Test Summary",
        "",
        "## Experiment Design",
        "",
        f"- Experiment: `{experiment['experiment_name']}`",
        f"- Control: {CONTROL.label}",
        f"- Treatment: {TREATMENT.label}",
        f"- Simulated users: {experiment['total_users']:,}",
        f"- Traffic split: {experiment['traffic_split_control']:.0%} control / "
        f"{1.0 - experiment['traffic_split_control']:.0%} treatment",
        f"- Required sample size per variant: {experiment['required_sample_size_per_variant']:,}",
        "",
        "## Variant Outcomes",
        "",
        "| Metric | Control A | Treatment B |",
        "|---|---:|---:|",
        f"| n | {control['n']:,} | {treatment['n']:,} |",
        f"| Successful answer rate | {control['success_rate']:.3f} | {treatment['success_rate']:.3f} |",
        f"| Average latency ms | {control['avg_latency_ms']:.2f} | {treatment['avg_latency_ms']:.2f} |",
        f"| P95 latency ms | {control['p95_latency_ms']:.2f} | {treatment['p95_latency_ms']:.2f} |",
        f"| Groundedness score | {control['avg_groundedness_score']:.3f} | "
        f"{treatment['avg_groundedness_score']:.3f} |",
        f"| Recall proxy | {control['avg_recall_proxy']:.3f} | {treatment['avg_recall_proxy']:.3f} |",
        f"| Error rate | {control['error_rate']:.3f} | {treatment['error_rate']:.3f} |",
        "",
        "## Primary Statistical Test",
        "",
        f"- Metric: `{primary['metric_name']}`",
        f"- Absolute lift: {primary['difference']:.4f}",
        f"- Relative lift: {primary['relative_lift']:.2%}",
        f"- p-value: {primary['p_value']:.6f}",
        f"- 95% CI: [{primary['ci_lower']:.4f}, {primary['ci_upper']:.4f}]",
        "",
        "## Guardrails",
        "",
        "| Metric | Passed | Reason |",
        "|---|---:|---|",
    ]

    for guardrail in guardrails:
        lines.append(
            f"| {guardrail['metric_name']} | {guardrail['passed']} | {guardrail['reason']} |"
        )

    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            f"`{report['recommendation']}`",
            "",
            "If this were an online deployment, the treatment should be rolled out only after "
            "production monitoring confirms that recall, error rate, and latency guardrails "
            "continue to hold under real traffic.",
            "",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_report(report: dict[str, object], output_dir: Path) -> None:
    """Write JSON and Markdown artifacts."""

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "ab_test_results.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    write_markdown_summary(report, output_dir / "ab_test_summary.md")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description="Run Final Project Component 2 A/B simulation.")
    parser.add_argument("--total-users", type=int, default=ExperimentConfig.total_users)
    parser.add_argument("--seed", type=int, default=ExperimentConfig.seed)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    """Entry point for the offline simulation."""

    args = parse_args()
    config = ExperimentConfig(total_users=args.total_users, seed=args.seed)
    observations = simulate_experiment(config)
    report = analyze_experiment(observations, config)
    write_report(report, args.output_dir)
    print(json.dumps({"recommendation": report["recommendation"]}, indent=2))


if __name__ == "__main__":
    main()
