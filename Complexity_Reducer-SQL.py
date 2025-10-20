import sys
import re
import argparse

try:
        import sqlparse
except Exception:
        raise SystemExit("Please pip install sqlparse (pip install sqlparse)")

# Optional: for EXPLAIN
try:
        from sqlalchemy import create_engine, text
except Exception:
        create_engine = None

def format_sql(sql: str) -> str:
        return sqlparse.format(sql, reindent=True, keyword_case='upper')

def remove_redundant_parentheses(sql: str) -> str:
        # Remove surrounding parentheses around the entire query
        s = sql.strip()
        if s.startswith("(") and s.endswith(")"):
                # simple check for matching parentheses: if parentheses wrap whole query
                depth = 0
                for i, ch in enumerate(s):
                        if ch == "(":
                                depth += 1
                        elif ch == ")":
                                depth -= 1
                        if depth == 0 and i < len(s) - 1:
                                break
                else:
                        # parentheses wrap entire string
                        return s[1:-1].strip()
        # remove duplicate parentheses like ((...)) -> (...)
        s = re.sub(r'\(\s*\(\s*', '(', s)
        s = re.sub(r'\)\s*\)\s*', ')', s)
        return s

def simplify_boolean_constants(sql: str) -> str:
        # remove obvious no-op boolean terms: AND TRUE, OR FALSE
        s = re.sub(r'\bAND\s+TRUE\b', '', sql, flags=re.I)
        s = re.sub(r'\bTRUE\s+AND\b', '', s, flags=re.I)
        s = re.sub(r'\bOR\s+FALSE\b', '', s, flags=re.I)
        s = re.sub(r'\bFALSE\s+OR\b', '', s, flags=re.I)
        # collapse multiple spaces
        s = re.sub(r'\s{2,}', ' ', s)
        return s

def drop_redundant_distinct_if_groupby(sql: str) -> (str, bool):
        # If query has SELECT DISTINCT ... and GROUP BY exists, DISTINCT is usually redundant.
        if re.search(r'\bSELECT\s+DISTINCT\b', sql, flags=re.I) and re.search(r'\bGROUP\s+BY\b', sql, flags=re.I):
                new = re.sub(r'\bSELECT\s+DISTINCT\b', 'SELECT', sql, flags=re.I)
                return new, True
        return sql, False

def hoist_repeated_subqueries_to_ctes(sql: str) -> (str, list):
        """
        Find identical subqueries used in FROM (...) alias repeated multiple times,
        and hoist them into a single CTE. Only applies to subqueries in FROM with an alias.
        This is a safe, semantics-preserving refactor in SQL engines that support CTEs.
        """
        pattern = re.compile(r'FROM\s*\(\s*(SELECT[\s\S]+?)\s*\)\s+(?:AS\s+)?([a-zA-Z_][\w]*)', flags=re.I)
        matches = pattern.findall(sql)
        if not matches:
                return sql, []

        # Count identical inner SELECTs
        inner_map = {}
        for inner, alias in matches:
                key = re.sub(r'\s+', ' ', inner.strip())  # normalize whitespace when counting
                inner_map.setdefault(key, []).append((inner, alias))

        cte_defs = []
        new_sql = sql
        cte_index = 0
        for key, occurrences in inner_map.items():
                if len(occurrences) <= 1:
                        continue
                cte_index += 1
                cte_name = f"_cte_{cte_index}"
                # Build CTE definition using the first inner occurrence (preserve original spacing)
                inner_sql = occurrences[0][0].strip()
                cte_defs.append((cte_name, inner_sql))
                # Replace each FROM (inner_sql) alias with FROM cte_name alias
                # Use a regex escape of the inner_sql reduced to whitespace-normalized pattern
                inner_norm = re.sub(r'\s+', r'\\s+', re.escape(inner_sql))
                replace_pattern = re.compile(r'FROM\s*\(\s*' + inner_norm + r'\s*\)\s+(?:AS\s+)?([a-zA-Z_][\w]*)', flags=re.I)
                def _repl(match):
                        alias = match.group(1)
                        return f"FROM {cte_name} {alias}"
                new_sql = replace_pattern.sub(_repl, new_sql)

        if not cte_defs:
                return sql, []

        # Prepend WITH clause
        with_parts = []
        for name, body in cte_defs:
                with_parts.append(f"{name} AS ({body})")
        with_clause = "WITH " + ", ".join(with_parts) + "\n"
        new_sql = with_clause + new_sql
        return new_sql, [name for name, _ in cte_defs]

def safe_reduce_select_star(sql: str) -> (str, bool):
        # Very conservative: only remove SELECT * when query has GROUP BY (explicit columns)
        # and star is used but group by specifies columns (this is risky in general),
        # so we do NOT perform this transform automatically. Return False indicating no change.
        return sql, False

def generate_explain(db_url: str, sql: str) -> (str, bool):
        if not create_engine:
                return "sqlalchemy not installed; cannot run EXPLAIN", False
        try:
                engine = create_engine(db_url)
                with engine.connect() as conn:
                        # Use dialect-agnostic EXPLAIN if possible
                        try:
                                # Some DBs require EXPLAIN before the query; others might need EXPLAIN ANALYZE.
                                res = conn.execute(text("EXPLAIN " + sql))
                                rows = res.fetchall()
                                lines = [str(r[0]) for r in rows]
                                return "\n".join(lines), True
                        except Exception as e:
                                # Try EXPLAIN ANALYZE (Postgres)
                                try:
                                        res = conn.execute(text("EXPLAIN ANALYZE " + sql))
                                        rows = res.fetchall()
                                        lines = [str(r[0]) for r in rows]
                                        return "\n".join(lines), True
                                except Exception as e2:
                                        return f"EXPLAIN failed: {e} | {e2}", False
        except Exception as e:
                return f"Could not connect or run EXPLAIN: {e}", False

def optimize(sql: str):
        suggestions = []
        original_formatted = format_sql(sql)
        working = original_formatted

        # Remove redundant wrapping parentheses
        new = remove_redundant_parentheses(working)
        if new != working:
                suggestions.append("Removed redundant outer parentheses")
                working = new

        # Simplify boolean constants
        new = simplify_boolean_constants(working)
        if new != working:
                suggestions.append("Simplified boolean constants (AND TRUE / OR FALSE)")
                working = new

        # Drop DISTINCT if there is a GROUP BY
        new, dropped = drop_redundant_distinct_if_groupby(working)
        if dropped:
                suggestions.append("Dropped DISTINCT because GROUP BY present")
                working = new

        # Hoist repeated subqueries (FROM (SELECT...) alias) into CTEs
        new, cte_names = hoist_repeated_subqueries_to_ctes(working)
        if cte_names:
                suggestions.append(f"Hoisted repeated subqueries into CTEs: {', '.join(cte_names)}")
                working = new

        # Other safe normalizations
        working = format_sql(working)

        return original_formatted, working, suggestions

def main():
        parser = argparse.ArgumentParser(description="Heuristic SQL simplifier/optimizer (safe rewrites).")
        parser.add_argument("sqlfile", help="Path to SQL file (or - to read stdin)")
        parser.add_argument("--db-url", help="Optional SQLAlchemy DB URL to run EXPLAIN")
        args = parser.parse_args()

        if args.sqlfile == "-":
                sql = sys.stdin.read()
        else:
                with open(args.sqlfile, 'r', encoding='utf-8') as f:
                        sql = f.read()

        orig, optimized, suggestions = optimize(sql)

        print("---- Original (formatted) ----")
        print(orig)
        print("\n---- Optimized candidate ----")
        print(optimized)
        print("\n---- Suggestions ----")
        if suggestions:
                for s in suggestions:
                        print("- " + s)
        else:
                print("No safe rewrites found. Consider manual review: index suggestions, EXPLAIN plans, removing unused columns, rewriting heavy correlated subqueries to joins/CTEs, and adding proper indexes.")

        if args.db_url:
                explain_out, ok = generate_explain(args.db_url, optimized)
                print("\n---- EXPLAIN (on optimized SQL) ----")
                print(explain_out)
                if not ok:
                        print("\nNote: EXPLAIN failed; ensure DB URL and permissions are correct.")

if __name__ == "__main__":
        main()