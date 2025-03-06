USE rdstest;
ALTER TABLE Fires
ADD COLUMN start_datetime TIMESTAMP NULL COMMENT 'Дата и время начала тушения',
ADD COLUMN localization_datetime TIMESTAMP NULL COMMENT 'Дата и время локализации',
ADD COLUMN liquidation_datetime TIMESTAMP NULL COMMENT 'Дата и время ликвидации';

ALTER TABLE Fires
MODIFY COLUMN damage_area DECIMAL(10,4) COMMENT 'Площадь пожара',
MODIFY COLUMN damage_les DECIMAL(10,4) COMMENT 'Лесная площадь пожара',
MODIFY COLUMN damage_les_lesopokryt DECIMAL(10,4) COMMENT 'Лесопокрытая площадь пожара',
MODIFY COLUMN damage_les_verh DECIMAL(10,4) COMMENT 'Верховая площадь пожара',
MODIFY COLUMN damage_not_les DECIMAL(10,4) COMMENT 'Нелесная площадь пожара';
