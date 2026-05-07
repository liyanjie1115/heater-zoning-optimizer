import argparse
import json

from .config import AnalysisConfig
from .runflow import run_analysis_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Heater zoning optimizer CLI")
    parser.add_argument("--input", help="Input CSV/XLSX profile path. Omit to use sample data.")
    parser.add_argument("--output-dir", default="outputs", help="Directory for Excel exports.")
    parser.add_argument("--output-name", help="Optional Excel filename.")
    parser.add_argument("--total-length", type=float, default=500.0)
    parser.add_argument("--max-zones", type=int, default=8)
    parser.add_argument("--equal-zone-count", type=int, default=8)
    parser.add_argument("--alpha", type=float, default=5.0)
    parser.add_argument("--module-length", type=float, default=23.0)
    parser.add_argument("--module-gap", type=float, default=10.0)
    parser.add_argument("--outer-edge-allow", type=float, default=10.0)
    parser.add_argument("--sample-left-ratio", type=float, default=0.30)
    parser.add_argument("--sample-mid-ratio", type=float, default=0.50)
    parser.add_argument("--sample-right-ratio", type=float, default=0.70)
    parser.add_argument("--fit-weight", type=float, default=0.32)
    parser.add_argument("--separation-weight", type=float, default=0.22)
    parser.add_argument("--gradient-weight", type=float, default=0.24)
    parser.add_argument("--heater-weight", type=float, default=0.12)
    parser.add_argument("--balance-weight", type=float, default=0.10)
    parser.add_argument("--fit-decay", type=float, default=850.0)
    parser.add_argument("--heater-decay", type=float, default=16.0)
    parser.add_argument("--internal-violation-penalty", type=float, default=0.18)
    parser.add_argument("--size-compliance-penalty", type=float, default=0.08)
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    config = AnalysisConfig(
        total_length=args.total_length,
        max_zones=args.max_zones,
        alpha=args.alpha,
        equal_zone_count=args.equal_zone_count,
        module_length=args.module_length,
        module_gap=args.module_gap,
        outer_edge_allow=args.outer_edge_allow,
        sample_left_ratio=args.sample_left_ratio,
        sample_mid_ratio=args.sample_mid_ratio,
        sample_right_ratio=args.sample_right_ratio,
        fit_weight=args.fit_weight,
        separation_weight=args.separation_weight,
        gradient_weight=args.gradient_weight,
        heater_weight=args.heater_weight,
        balance_weight=args.balance_weight,
        fit_decay=args.fit_decay,
        heater_decay=args.heater_decay,
        internal_violation_penalty=args.internal_violation_penalty,
        size_compliance_penalty=args.size_compliance_penalty,
    ).validate()

    artifacts = run_analysis_pipeline(
        config=config,
        source="upload" if args.input else "sample",
        file_path=args.input,
        output_dir=args.output_dir,
        output_name=args.output_name,
    )

    payload = {
        "export_path": str(artifacts.export_path),
        "recommended": artifacts.summary_cards[0]["value"],
        "equal_score": artifacts.result.equal_metrics.composite_score,
        "aligned_score": artifacts.result.aligned_metrics.composite_score,
        "equal_zone_count": len(artifacts.result.equal_zones),
        "aligned_zone_count": len(artifacts.result.aligned_zones),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"导出完成: {payload['export_path']}")
        print(f"推荐方案: {payload['recommended']}")
        print(f"等距分区得分: {payload['equal_score']:.3f}")
        print(f"模块对齐得分: {payload['aligned_score']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
