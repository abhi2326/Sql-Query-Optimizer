-- Sample complex SQL query for testing the optimizer
SELECT DISTINCT 
    u.user_id,
    u.username,
    u.email,
    COUNT(o.order_id) as total_orders,
    SUM(o.total_amount) as total_spent
FROM (
    SELECT user_id, username, email 
    FROM users 
    WHERE status = 'active' AND created_at > '2023-01-01'
) u
JOIN (
    SELECT user_id, order_id, total_amount 
    FROM orders 
    WHERE status = 'completed' AND order_date > '2023-01-01'
) o ON u.user_id = o.user_id
WHERE u.user_id IN (
    SELECT user_id 
    FROM user_preferences 
    WHERE newsletter = TRUE AND notifications = TRUE
)
GROUP BY u.user_id, u.username, u.email
HAVING COUNT(o.order_id) > 5 AND SUM(o.total_amount) > 1000
ORDER BY total_spent DESC
LIMIT 10;
