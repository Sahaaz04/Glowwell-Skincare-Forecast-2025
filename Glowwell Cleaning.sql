DROP TABLE IF EXISTS df;

CREATE TABLE df (
"Date" TIMESTAMP,
"Product_Name" TEXT,
"State" TEXT,
"Units_Sold" INT,
"Stock_On_Hand" INT,
"Selling_Price" FLOAT,
"Competitor_A_Price" FLOAT,
"Competitor_B_Price" FLOAT
);

COPY df (
"Date",
"Product_Name",
"State",
"Units_Sold",
"Stock_On_Hand",
"Selling_Price",
"Competitor_A_Price",
"Competitor_B_Price"
)
FROM 'C:\Program Files\Analysis\Glowwell Skincare Sales 2022-2024 (Raw).csv'
DELIMITER ','
CSV HEADER;

-- Turning all empty ' ' strings into null values and removing spaces in front or back of strings.
UPDATE df
SET
  "Product_Name" = NULLIF(TRIM("transaction_id"), ''),
  "State"        = NULLIF(TRIM("customer_id"), '');

-- Finding Duplicates and near Duplicates.

-- SELECT DISTINCT "State" FROM df;
-- SELECT DISTINCT "Product_Name" FROM df;

UPDATE df
SET "Product_Name" = 'Moisturizer'
WHERE "Product_Name" = 'Moisturiser';

UPDATE df
SET "State" = "CA"
WHERE "State" = "CAM";

-- 2. Check for negative values
-- SELECT * FROM df
-- WHERE "Units_Sold" < 0 OR quantity < 0;

-- 2. Check for negative values
-- SELECT * FROM df
-- WHERE "Stock_On_Hand" < 0 OR quantity < 0;

-- 2. Check for negative values
-- SELECT * FROM df
-- WHERE "Selling_Price" < 0 OR quantity < 0;




-- Cross Validating Date-Time
SELECT 
  MIN("transaction_date") AS earliest, 
  MAX("transaction_date") AS latest 
FROM df;


--  Transactions Table Cleaning Report


-- - Trimmed all string values
-- - Checked Anomalies and Outliers
-- - Verified duplicates and near-duplicates
-- - Cross Validated Date-Time

