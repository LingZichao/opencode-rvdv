# Trace Benchmark

## 职责边界

- `test_plan.md`
  是交给 generator 的输入，必须是纯行为描述，不能携带参考文件路径、API 名称清单或“先看什么再看什么”之类的检索指令。
- `manifest.yaml`
  是实验与标注侧元数据，负责记录这个 case 期望命中的 example/api section、风险等级、trace 验收规则。
- `unit_catalog.yaml`
  是标注层的知识单元目录，服务于后续 trace 映射与质量统计，不直接暴露给 generator。

## 当前范围

- 已覆盖 20 个手工 seed case，包含基础类与高风险 stretch 类
- 当前已落地主题方向：
  - register/dependency
  - branch/control-flow
  - address/memory
  - floating-point/data-constraint
  - state/system-register
  - privilege-switch/paging-fault（高风险）
  - misaligned-access/exception-recovery（高风险）
  - exception-delegation/privilege-roundtrip（高风险）
  - speculative-branch/reconverge（高风险）
  - vector-masked-memory/attribute-contrast（高风险，历史遗留，不再扩展）
  - exception-history/correlation（高风险）
  - paging-attributes/page-crossing（高风险）
  - privilege-switch/syscall-roundtrip（高风险）
  - ifetch-misaligned/access-fault-mix（高风险）
  - invalid-address/alias-contrast（高风险）
  - exception-handler/stack-integrity（高风险）
  - compressed-instruction/control-alignment（高风险）
  - page-allocation/fragmentation-stress（高风险）
  - ooo-scheduling/scoreboard-hazard（高风险，微架构专项）
  - lsu-forwarding/memory-order-window（高风险，微架构专项）
- 暂不引入 embedding、层次聚类、自动切分或批量 case 扩展

## 计划对齐约束（新增）

- 后续新增 case 禁止使用向量主线（vector/vsetvl/vsetvli/vector load-store）。
- 已存在的向量 case 仅作为历史样本保留，不纳入后续扩展方向。
- 新增 case 的主题范围仅限：
  - register/dependency
  - branch/control-flow
  - address/memory
  - floating-point/data-constraint
  - state/system-register
  - exception/privilege/paging/misaligned（非向量）

## 目录说明

- `unit_catalog.yaml`
  记录本轮手工打标的 `nav_unit / example / apiDoc_section` 单元，字段保持与后续自动化方案兼容。
- `cases/case_*/manifest.yaml`
  每个测试用例的标注 manifest，包含 `cluster_id`、`primary_example_unit`、`required_api_units`、`risk_tier`、`expected_source_mix` 等核心字段。
- `cases/case_*/test_plan.md`
  可直接投喂给 WebUI/Agent 的 generator 输入，只保留行为目标和约束。

## 手工打标原则

1. 先只标注当前 case 真正需要访问的 unit，不追求一次性覆盖全部知识库。
2. `required_api_units` 只放那些会决定实现正确性的 API section，但它们属于评测标签，不属于 generator 输入。
3. generator 看到的 `test_plan` 只描述目标行为、结构边界和完成条件，不规定实现路径。
4. “example 风格约束”和“api-sensitive 语义陷阱”放进 manifest 的标注字段，而不是写进 generator 输入。
5. 目录和字段命名优先保持未来可扩展性，避免后续切回聚类版时返工 schema。

## 当前质量检查点

- case 是否能明确逼出 `example + apiDoc` 双源检索
- case 是否能把 `Write` 与 `ReadWrite` 这类容易误用的 API 语义暴露出来
- manifest 的字段是否足够支撑后续 trace 对齐和命中统计
