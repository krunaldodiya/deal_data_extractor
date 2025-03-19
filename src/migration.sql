-- Drop any constraints that reference dealstatus
ALTER TABLE deal_tasks
  ALTER COLUMN status DROP DEFAULT;

-- Temporarily convert the column to text
ALTER TABLE deal_tasks
  ALTER COLUMN status TYPE text;

-- Drop the enum type
DROP TYPE IF EXISTS dealstatus;

-- Create the enum with correct values
CREATE TYPE dealstatus AS ENUM ('PENDING', 'PROCESSING', 'SUCCESS', 'FAILED');

-- Convert the status column back to enum
UPDATE deal_tasks SET status = 'PENDING' WHERE status IN ('pending', '');
UPDATE deal_tasks SET status = 'PROCESSING' WHERE status = 'processing';
UPDATE deal_tasks SET status = 'SUCCESS' WHERE status = 'success';
UPDATE deal_tasks SET status = 'FAILED' WHERE status = 'failed';

ALTER TABLE deal_tasks 
  ALTER COLUMN status TYPE dealstatus USING status::dealstatus;

-- Reset the default
ALTER TABLE deal_tasks
  ALTER COLUMN status SET DEFAULT 'PENDING';

-- Drop foreign key constraint between deals and deal_tasks
ALTER TABLE deals
  DROP CONSTRAINT IF EXISTS deals_deal_task_id_fkey;

-- Drop the deal_task_id column from deals
ALTER TABLE deals
  DROP COLUMN IF EXISTS deal_task_id; 