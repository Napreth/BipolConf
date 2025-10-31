# BipolConf

BipolConf 是一个以命名空间为基础，通过双向策略控制实现可验证继承的配置系统。
它将配置的传播与访问行为视为“策略决策”，而非单纯的键值查找，强调可验证性与模块自治。

## 设计理念概述

**核心定义：**
BipolConf 是一个以命名空间为基础、通过双向策略控制实现可验证继承的配置系统。
它将配置的传播与访问行为视为“策略决策”，而非“键值查找”。

### 1. 命名空间分层（Hierarchical Namespace）

配置被组织为树状结构（如 `page.home.router`），每个节点拥有独立的配置域（scope），并按层级形成作用域链。
查找遵循“从具体到泛化”的短路策略：`page.home.router → page.home → page → *`

### 2. 双向策略继承（Bidirectional Policy Inheritance）

继承不再是单向的“父传子”，而是由两个方向同时决定：

- 向上策略（`__up_policies__`）：子节点声明自己“愿意继承哪些键”；
- 向下策略（`__down_policies__`）：父节点声明自己“允许哪些键被继承”。

最终生效的继承由逻辑表达式决定：
`effective = allow_down(parent, key, child) AND allow_up(child, key)`

### 3. 遮蔽式继承（Shadowing Inheritance）

同名键在子节点出现时，完全覆盖父节点的定义；不会进行合并、叠加或类型融合。
每个节点只看到当前策略允许可见的部分父配置，其余对它是“黑盒”。

### 4. 短路查找（Short-circuit Lookup）

配置查询为确定性链式搜索：一旦在某层找到匹配项，立即返回；若策略拒绝继承，则链路中断。
此模型可映射为有限状态机，行为可预测且可验证。

### 5. 策略优先级体系（Policy Precedence）

继承控制规则具有分层优先级：

例外策略 (A) > 子节点或键级策略 (B1/B2) = 全局策略 (C)
(B 和 C 互斥)

确保在复杂配置中仍能得到唯一、可证明的决策结果。

### 6. 节点自治（Configuration Autonomy）

每个配置节点都是自治单元：

- 决定自己能继承什么；
- 决定自己能被谁继承。

这种设计让模块间配置具备清晰边界，避免全局污染。

### 总述

> BipolConf 将配置继承转化为可验证的策略决策过程，以命名空间划定作用域，以双向策略确定可见域，从而在灵活性与控制性之间取得严格平衡。

## 策略说明

下面是 `__up_policies__` 与 `__down_policies__` 的策略类型列表，以及每个策略类型的语义与示例。

### 向上继承策略（__up_policies__）——子节点声明“愿意继承什么”

结构示例（JSON）：

```json
"__up_policies__": [
	["策略类型"],
	{"详细配置": {}}
]
```

策略类型说明：

| 策略 | 说明 |
|------|------|
| *inherit | （默认）允许从父节点继承所有配置 |
| no-inherit | 不从父节点继承任何配置（断开继承链） |
| partial-inherit | 仅继承白名单中的配置项 |
| partial-no-inherit | 禁止继承黑名单中的配置项 |

示例：

```json
"page.home": {
	"__up_policies__": [
		"pattern": ["partial-inherit"],
		"keys": {
			"partial-inherit": ["theme", "language"]
		}
	],
	"timeout": 2000
}
```

说明：以上示例表示 `page.home` 仅愿意继承 `theme` 与 `language` 两个键（其余键即使父节点有也不可见）。

### 向下继承策略（__down_policies__）——父节点声明“允许子节点继承什么”

`__down_policies__` 控制当前节点的配置如何被子节点继承：

策略类型说明：

| 策略 | 说明 |
|------|------|
| *inheritable | （默认）允许所有子节点继承所有配置 |
| uninheritable | 不允许任何子节点继承任何配置 |
| partial-inheritable | 仅白名单中的配置项可被继承 |
| partial-uninheritable | 黑名单中的配置项不可被继承 |
| partial-subnode-inheritable | 仅白名单中的子节点可继承 |
| partial-subnode-uninheritable | 黑名单中的子节点不可继承 |
| partial-inheritable-for-partial-subnode | 特定配置项仅对特定子节点可继承 |
| partial-uninheritable-for-partial-subnode | 特定配置项对特定子节点不可继承 |

结构与示例：

```json
"page": {
	"__down_policies__": [
		"pattern": ["partial-inheritable", "partial-subnode-inheritable"],
		"keys": {
			"partial-inheritable": ["theme", "language"],
			"partial-subnode-inheritable": ["page.home", "page.blog"],
			"partial-inheritable-for-partial-subnode": {
				"theme": ["page.home"],
				"debug": ["page.admin"]
			}
		}
	],
	"theme": "dark",
	"debug": false,
	"api_key": "secret"
}
```

说明要点：

- `__up_policies__` 与 `__down_policies__` 是互相配合的：最终能否继承由 `allow_down(parent,key,child) AND allow_up(child,key)` 决定；
- 当父节点使用全局策略（例如 `uninheritable`）时，不允许任何向上继承；若父节点使用部分策略（`partial-*`），则需结合 keys/子节点白名单或黑名单判断；
- 某些策略用于分别限定“哪些键可继承”与“哪些子节点可继承”，还可以通过 `partial-inheritable-for-partial-subnode` / `partial-uninheritable-for-partial-subnode` 做细粒度例外控制。

请参考上面的 JSON 示例来书写策略；在更复杂的场景下，建议先用小范围的测试配置验证策略效果。

## 快速开始

1. 在仓库根目录创建或编辑 `config.json`（示例见项目文档或 README 的示例节）。
2. 在项目根目录运行：

```powershell
python -c "from src.config import Config; cfg=Config('page.home.router'); print(cfg.timeout)"
```

确保你的当前工作目录为仓库根目录，使 `config.json` 可被模块以相对路径加载。

## 扩展方向

- 支持可配置的配置文件路径与延迟加载；
- 提供更友好的公开 API（`get`/`set`/`save`/`reload`）与单元测试覆盖关键策略组合；
- 改进策略声明的 JSON Schema，并添加验证逻辑以便早期报警策略冲突。

