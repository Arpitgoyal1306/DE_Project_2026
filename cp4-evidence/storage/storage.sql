-- 1. Whole database size
SELECT
    current_database() AS database_name,
    pg_size_pretty(pg_database_size(current_database())) AS database_size,
    pg_database_size(current_database()) AS database_bytes;

-- 2. Heap, index and total size by logical table.
-- Partition sizes are grouped under their parent table.
SELECT
    COALESCE(parent.relname, c.relname) AS table_name,
    pg_size_pretty(SUM(pg_relation_size(c.oid))) AS heap_size,
    pg_size_pretty(SUM(pg_indexes_size(c.oid))) AS indexes_size,
    pg_size_pretty(SUM(pg_total_relation_size(c.oid))) AS total_size,
    SUM(pg_relation_size(c.oid)) AS heap_bytes,
    SUM(pg_indexes_size(c.oid)) AS index_bytes,
    SUM(pg_total_relation_size(c.oid)) AS total_bytes
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_inherits i ON i.inhrelid = c.oid
LEFT JOIN pg_class parent ON parent.oid = i.inhparent
WHERE n.nspname = 'bms'
  AND c.relkind = 'r'
GROUP BY COALESCE(parent.relname, c.relname)
ORDER BY SUM(pg_total_relation_size(c.oid)) DESC;

-- 3. Individual booking_seats partition sizes
SELECT
    c.relname AS partition_name,
    pg_size_pretty(pg_relation_size(c.oid)) AS heap_size,
    pg_size_pretty(pg_indexes_size(c.oid)) AS indexes_size,
    pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
    pg_total_relation_size(c.oid) AS total_bytes
FROM pg_inherits i
JOIN pg_class p ON p.oid = i.inhparent
JOIN pg_class c ON c.oid = i.inhrelid
JOIN pg_namespace n ON n.oid = p.relnamespace
WHERE n.nspname = 'bms'
  AND p.relname = 'booking_seats'
ORDER BY c.relname;
