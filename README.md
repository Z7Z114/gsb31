# Jack — a Blackjack engine in Python 3

Jack is a Blackjack game engine. It deals from a shoe, plays each hand with basic
strategy, settles the round against the dealer and can simulate many games in a row.
House rules and the strategy tables are meant to be configurable.

- `lib/Jack.py` — the table: dealing, one player's turn, the dealer's turn, settling a round
- `lib/Player.py` — a player, their hands, their per-game accounting
- `lib/Hand.py`, `lib/Card.py`, `lib/Shoe.py` — hands, single cards, the shoe
- `lib/Utils.py` — blackjack arithmetic (card values, soft totals, blackjack/bust checks)
- `lib/BasicStrategy.py` — the decision matrices and the row/column lookups into them
- `test/` — the test suite; `test_runner.py` runs it with unittest
- `experiments.ipynb` — the demo notebook showing the intended way to drive the engine

## Running it

Plain local Python 3 plus `numpy` (only `BasicStrategy` needs it, for the matrices).
Nothing is containerised here: no `Dockerfile`, no compose file, no service to start,
no network access and no external card/hand API — everything is in-process.

```
pip install numpy
python test_runner.py        # unittest, the way this repo has always run it
python -m pytest -q          # same suite under pytest
```

## Gameplay assumptions

- stand on soft 17
- 8 deck shoe
- double down allowed after pair splitting (DAS)
- second splits (and resplits in general) allowed
- every bet is 1 unit

The `TODO` items in the upstream notes (variable betting, alternative strategies,
configurable logging) are **not** part of the acceptance criteria below.

## 行为规格（验收标准）

下面是本项目的验收标准，每条都是可测试的客观条款。改动以这里为准，不要以「已知问题」
为准。「已知问题」只是部分现象，写得不全。

**1. 玩家结算 `lib/Player.py`**

1.1 新建的 `Player` 必须有一个从 0 开始的 `bankroll`。

1.2 `Player.update_bankroll()` 必须把 `recent_winloss` 里的每一笔结果累加进 `bankroll`，
然后把 `recent_winloss` 清空（调用后 `recent_winloss == []`）。

1.3 `Player.reset()` / `clear_hands()` / `units_spent` / `recent_winloss` 的既有语义不变：
`clear_hands()` 只重置手牌，跨局的累计统计仍然保留（`experiments.ipynb` 依赖这一点）。

**2. 点数计算 `lib/Utils.py`**

2.1 `Utils.card_value` 的算法不变：A 默认 11，超 21 时逐个降为 1，直到不超过 21。

2.2 `Utils.has_soft_total(cards)`：只要手牌中存在一张 A 可以按 11 计而不爆牌，就必须返回
`True`。多张 A 的手牌同样适用：`[A, A, 2]` 的合法点数有 4 和 14，必须返回 `True`；
`[A, A, 3]` → `True`；`[A, 3, 3]` → `True`；`[A, 3, 3, 6]`（13 点，A 只能是 1）→ `False`。

**3. 对子判定 `lib/Jack.py` 的 `has_double`**

3.1 两张**点数相同**的牌就是可拆的对子，包括牌面名字不同但点数相同的组合：
`[10, J]`、`[J, Q]`、`[10, K]` 都必须返回 `True`；`[8, 8]` → `True`。

3.2 点数不同的两张牌 → `False`（如 `[8, 7]`）。传入手牌数不等于 2 时仍然抛 `ValueError`。

**4. 拆牌后可以加倍（DAS）`lib/Jack.py` 的 `turn`**

4.1 README 的规则是「拆牌后允许加倍」。拆出来的手牌在拿到第二张牌后的那个决策点上，
如果策略给出 `ddown`，必须真的加倍：`hand.units` 从 1 变成 2、`hand.status == 'ddown'`、
只多拿一张牌，并且 `Player.units_spent` 与所有 `hand.units` 之和保持一致。

4.2 已经摸过牌（3 张及以上）的手牌不能加倍，这时 `ddown` 仍然按 hit 处理。

**5. `ddownS` 的 stand 分支 `lib/Jack.py` 的 `turn`**

5.1 `ddownS` 的含义是「不能加倍时就 stand」。当一手牌不能加倍、策略给出 `ddownS` 时，
必须直接 stand：`hand.status == 'stand'`，并且**不得再摸牌**，结算按 stand 时的点数比大小。

**6. 投降（sur）的兜底 `lib/Jack.py` 的 `turn`**

6.1 `sur` 只在首轮两张牌时有效，状态为 `sur`，结算按 `units / 2` 赔付。

6.2 当策略在非首轮（已经摸过牌的手牌、或拆出来的手牌）给出 `sur` 时，`turn` 结束时手牌
必须停在终态（`stand`、`busted`、`unnat`、`blackjack` 或 `ddown`），不能停在 `hit`：既然投降
不可用，就按 hit 继续走完这手牌。

**7. 回归约束**

7.1 `test/` 下已有的用例是回归基线，必须保持全绿。

7.2 不允许放宽、删除或跳过既有断言；自己补的测试必须在修复前失败、修复后通过，不能是
永远为真的空断言。

## 已知问题（不完整清单，不是验收标准）

- 有人想用 `update_bankroll()` 把一局的结果并进钱包，结果直接报错；就算先把
  `bankroll` 建好，调用完待结算的记录也还在。
- 有人发现某几手牌明明是软 14，引擎却当成硬牌来决策。
- 有人拿到 10 和 J 想拆牌，引擎说这不是对子。
- 有人拆牌之后想加倍，引擎不认；也有几手牌打完以后状态还停在 `hit`。

以上只是玩家能看到的一部分现象。请以「行为规格（验收标准）」为准，自己把条款对应的问题
找全；只修上面这几条不算完成。

## Misc

Blackjack rules reference: https://wizardofvegas.com/guides/blackjack-survey/
DOA = double on anything, DAS = double after split. Most 6-8 deck Vegas games are DOA + DAS.
