# Feb 23 12:31
ALTER TABLE IF EXISTS public.imu_measurement
ADD COLUMN frame_id bigint;

ALTER TABLE IF EXISTS public.imu_measurement
ADD COLUMN capture_time double precision;

UPDATE public.imu_measurement
SET frame_id = 0
WHERE frame_id IS NULL;

UPDATE public.imu_measurement
SET "capture_time (device)" = 0
WHERE "capture_time (device)" IS NULL;

<!-- ALTER TABLE IF EXISTS public.imu_measurement
    ALTER COLUMN frame_id SET NOT NULL;

ALTER TABLE IF EXISTS public.imu_measurement
    ALTER COLUMN "capture_time (device)" SET NOT NULL; -->