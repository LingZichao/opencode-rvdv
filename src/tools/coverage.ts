import { query_baseline_coverage, query_coverage, list_coverage_tests } from "./coverage_query"
import { fetch_coverage_report } from "./coverage_fetch"

export const coverage_tools = {
  query_baseline_coverage,
  query_coverage,
  list_coverage_tests,
  fetch_coverage_report,
}