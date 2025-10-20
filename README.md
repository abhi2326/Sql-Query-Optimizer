🧠 SQL Optimizer & Formatter  
A lightweight, safe SQL simplifier and optimizer built with Python.
!Python
!License
!SQL
!Status
***🚀 Overview
This project is a heuristic SQL simplifier and optimizer that performs safe, non-destructive rewrites of SQL queries to improve readability and potential performance — without altering query semantics.  
It can:
Reformat SQL into clean, consistent style  
Remove redundant parentheses  
Simplify boolean expressions (AND TRUE, OR FALSE)  
Drop unnecessary DISTINCT when GROUP BY exists  
Hoist repeated subqueries into CTEs (Common Table Expressions)  
Optionally generate EXPLAIN plans to visualize query performance
***🧩 Features
✅ Smart Formatting: Beautifies messy SQL using sqlparse  
✅ Boolean Simplification: Cleans redundant logical constants  
✅ CTE Hoisting: Detects repeated subqueries and merges them  
✅ Redundancy Cleanup: Removes unnecessary constructs  
✅ Explain Support: Integrates with SQLAlchemy to run EXPLAIN or EXPLAIN ANALYZE  
✅ Safe Transformations: Never changes query logic  
***📂 Project Structure
📦 SQL-Optimizer
 ┣ 📜 optimizer.py          # Main script
 ┣ 📜 requirements.txt      # Dependencies
 ┣ 📜 example.sql           # Sample SQL to test
 ┗ 📘 README.md             # This file
***🧠 Example Usage
🔹 Input
SELECT DISTINCT u.user_id, u.username, u.email, COUNT(o.order_id)
FROM (SELECT * FROM users WHERE status = 'active') u
JOIN (SELECT * FROM orders WHERE status = 'completed') o ON u.user_id = o.user_id
WHERE u.user_id IN (SELECT user_id FROM prefs WHERE newsletter = TRUE AND notifications = TRUE)
GROUP BY u.user_id, u.username, u.email
HAVING COUNT(o.order_id) > 5
ORDER BY COUNT(o.order_id) DESC;
🔹 Output
WITH _cte_1 AS (
    SELECT * FROM users WHERE status = 'active'
),
_cte_2 AS (
    SELECT * FROM orders WHERE status = 'completed'
)
SELECT 
    u.user_id,
    u.username,
    u.email,
    COUNT(o.order_id)
FROM _cte_1 u
JOIN _cte_2 o ON u.user_id = o.user_id
WHERE u.user_id IN (
    SELECT user_id
    FROM prefs
    WHERE newsletter = TRUE AND notifications = TRUE
)
GROUP BY u.user_id, u.username, u.email
HAVING COUNT(o.order_id) > 5
ORDER BY COUNT(o.order_id) DESC;
🪄 Suggestions Generated:
- Dropped DISTINCT because GROUP BY present
- Hoisted repeated subqueries into CTEs: _cte_1, _cte_2
***⚙️ Installation
1️⃣ Clone the Repository
git clone https://github.com/abhijeet-sri11/SQL-Optimizer.git
cd SQL-Optimizer
2️⃣ Install Dependencies
pip install -r requirements.txt
(If you don’t have requirements.txt, simply run:)
pip install sqlparse sqlalchemy
***🧰 Usage
▶️ Basic Run
python optimizer.py example.sql
▶️ Using Standard Input
cat example.sql | python optimizer.py -
▶️ With EXPLAIN (requires DB URL)
python optimizer.py example.sql --db-url "postgresql://user:pass@localhost/dbname"
***🧩 Example Output
---- Original (formatted) ----
<beautiful formatted SQL>
---- Optimized candidate ----
<optimized query with refactors>
---- Suggestions ----
- Removed redundant outer parentheses
- Simplified boolean constants
- Hoisted repeated subqueries into CTEs: _cte_1
***🧩 Modules Overview
| Function | Purpose |
|-----------|----------|
| format_sql() | Cleans and indents SQL with sqlparse |
| remove_redundant_parentheses() | Removes unnecessary outer parentheses |
| simplify_boolean_constants() | Strips AND TRUE, OR FALSE |
| drop_redundant_distinct_if_groupby() | Detects redundant DISTINCT |
| hoist_repeated_subqueries_to_ctes() | Promotes repeated subqueries into CTEs |
| generate_explain() | Runs EXPLAIN/ANALYZE via SQLAlchemy |
| optimize() | Central orchestration logic |
| main() | CLI interface for file or stdin input |
***🧩 Example DB URL formats
PostgreSQL → postgresql://username:password@localhost:5432/dbname
MySQL → mysql+pymysql://username:password@localhost/dbname
SQLite → sqlite:///path/to/database.db
***🧑‍💻 Author
Abhijeet Srivastava  
📍 Developer • Machine Learning & Data Engineering Enthusiast  
🔗 LinkedIn  
💻 GitHub
***📜 License
This project is licensed under the MIT License — free to use, modify, and distribute.
***💡 Future Enhancements
Add support for detecting unused columns in SELECT *
Add index suggestion hints via EXPLAIN plan parsing
Visualize query execution trees
Integrate with Jupyter notebooks
