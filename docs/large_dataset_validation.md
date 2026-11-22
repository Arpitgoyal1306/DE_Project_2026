# Large Dataset Validation

**Date:** 2026-11-22  
**Database:** de_project_2026  
**Schema:** bms  
**Import script:** sql/07_load_large_data.sql

## Import process

The large CSV dataset was imported into the local PostgreSQL database
using the `\copy` commands in `sql/07_load_large_data.sql`.

All 11 tables were loaded in foreign-key dependency order.
The import script also performed row-count validation and ran ANALYZE.

## Verified row counts

| Table | Rows |
|---|---:|
| cities | 10 |
| venues | 2,800 |
| screens | 9,800 |
| seats | 1,879,182 |
| movies | 6,000 |
| shows | 3,201,268 |
| customers | 800,000 |
| offers | 25 |
| bookings | 3,004,077 |
| booking_seats | 6,016,946 |
| movie_reviews | 651,398 |
| **Total** | **15,571,506** |

## Validation result

All 11 database table counts matched their corresponding CSV data row
counts. The import transaction completed successfully with COMMIT.

An independent SQL COUNT(*) verification was also performed after import.
