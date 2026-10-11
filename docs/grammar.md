# CodeForge grammar

This is the formal grammar of the C subset that CodeForge accepts, written in EBNF.
`parser.py` follows it rule by rule: **each rule below is one method in the parser**.

Notation: `"int"` is a literal token, `IDENT`, `INT_CONST` and `STRING` are token
categories from the lexer, `[ x ]` means optional, `( x )*` means zero or more,
`x+` means one or more.

```
program      -> function+ EOF
function     -> "int" IDENT "(" [ params ] ")" block
params       -> "int" IDENT ( "," "int" IDENT )*

block        -> "{" statement* "}"
statement    -> block
              | declaration
              | ifStmt
              | whileStmt
              | returnStmt
              | printfStmt
              | assignment
              | callStmt

declaration  -> "int" IDENT [ "=" expression ] ";"
assignment   -> IDENT "=" expression ";"
callStmt     -> call ";"
ifStmt       -> "if" "(" expression ")" statement [ "else" statement ]
whileStmt    -> "while" "(" expression ")" statement
returnStmt   -> "return" expression ";"
printfStmt   -> "printf" "(" STRING ( "," expression )* ")" ";"

expression   -> logicOr
logicOr      -> logicAnd   ( "||" logicAnd )*
logicAnd     -> equality   ( "&&" equality )*
equality     -> relational ( ( "==" | "!=" ) relational )*
relational   -> additive   ( ( "<" | "<=" | ">" | ">=" ) additive )*
additive     -> term       ( ( "+" | "-" ) term )*
term         -> unary      ( ( "*" | "/" | "%" ) unary )*
unary        -> ( "-" | "!" ) unary | primary
primary      -> INT_CONST | IDENT | call | "(" expression ")"
call         -> IDENT "(" [ expression ( "," expression )* ] ")"
```

## Operator precedence (highest first)

| Level | Operators | Associativity | Parser method |
|---|---|---|---|
| 1 | `( )` grouping, function call | n/a | `_primary` |
| 2 | unary `-` `!` | right | `_unary` |
| 3 | `*` `/` `%` | left | `_term` |
| 4 | `+` `-` | left | `_additive` |
| 5 | `<` `<=` `>` `>=` | left | `_relational` |
| 6 | `==` `!=` | left | `_equality` |
| 7 | `&&` | left | `_logic_and` |
| 8 | `\|\|` | left | `_logic_or` |

Assignment `=` is a statement, not an expression, so `a = b = 3;` is not allowed.

## Design notes

- **Precedence by grammar layering.** The rule for a lower-precedence operator is
  written in terms of the next-higher level. So `*` can only appear *below* `+` in
  the tree, which makes `2 + 3 * 4` mean `2 + (3 * 4)` without any special code.
- **No left recursion.** A rule such as `additive -> additive "+" term` would make a
  recursive-descent parser call itself forever. We rewrite it as a loop
  (`term ( "+" term )*`) and build the tree to the left, which gives left associativity:
  `10 - 4 - 3` is `(10 - 4) - 3`.
- **Lookahead.** Almost every decision needs only the next token (LL(1)). The only
  exception is a statement or primary that starts with `IDENT`: we need the token
  *after* it (`=` or `(`) to tell an assignment from a call, and a variable from a call.
  That makes the grammar LL(2), which is easy for a hand-written parser.
- **Dangling else.** In `if (a) if (b) x; else y;` the `else` attaches to the nearest
  `if`. The parser does this naturally because it looks for `else` immediately after
  parsing the inner statement.
- **Parentheses are not stored in the AST.** The shape of the tree already records
  the grouping, so no `Paren` node is needed.
- **Things checked later, not by the parser.** Whether a variable is declared, whether a
  function exists, whether the call has the right number of arguments, and whether a
  `printf` format matches its arguments are *semantic* checks (next phase).
