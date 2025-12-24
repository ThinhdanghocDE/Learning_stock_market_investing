-- Migration: Thêm cột blocked_cash vào bảng portfolios
-- Chạy script này để thêm cột blocked_cash vào database

ALTER TABLE portfolios 
ADD COLUMN IF NOT EXISTS blocked_cash NUMERIC(15, 2) DEFAULT 0.00 NOT NULL;

-- Cập nhật tất cả portfolios hiện có để blocked_cash = 0
UPDATE portfolios SET blocked_cash = 0.00 WHERE blocked_cash IS NULL;

-- Comment
COMMENT ON COLUMN portfolios.blocked_cash IS 'Tiền bị phong tỏa từ QUEUED/PENDING orders (VND)';

