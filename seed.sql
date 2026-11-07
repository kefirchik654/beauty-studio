-- Тестовые данные: один салон, два мастера, пять услуг.
INSERT INTO salons (id, name, address, phone, hours_text, map_url)
VALUES (1, 'BEAUTY STUDIO', 'г. Красноярск, адрес салона', '+7 000 000-00-00',
        'Ежедневно с 10:00 до 21:00', 'https://maps.example.com/');

INSERT INTO masters (id, salon_id, name, specialization, experience_years) VALUES
  (1, 1, 'Анна',  'Парикмахер-стилист', 5),
  (2, 1, 'Мария', 'Колорист',           8);

INSERT INTO service_categories (id, salon_id, name, sort) VALUES
  (1, 1, 'Стрижки', 1), (2, 1, 'Окрашивание', 2), (3, 1, 'Укладки', 3);

INSERT INTO services (id, salon_id, category_id, name, price, price_from, duration_min, buffer_min) VALUES
  (1, 1, 1, 'Мужская стрижка',  900,  false, 45, 0),
  (2, 1, 1, 'Женская стрижка', 1500,  false, 60, 0),
  (3, 1, 2, 'Окрашивание',     3000,  true,  90, 15),
  (4, 1, 3, 'Укладка',         1000,  false, 45, 0);

INSERT INTO master_services (master_id, service_id, price_override) VALUES
  (1, 1, NULL), (1, 2, NULL), (1, 4, NULL),
  (2, 2, 1800), (2, 3, NULL), (2, 4, NULL);

-- Анна: пн–пт 10:00–19:00, обед 13:00–14:00
INSERT INTO working_hours (master_id, dow, start_time, end_time)
SELECT 1, d, '10:00', '19:00' FROM generate_series(0, 4) d;
INSERT INTO breaks (master_id, dow, start_time, end_time)
SELECT 1, d, '13:00', '14:00' FROM generate_series(0, 4) d;

-- Мария: вт–сб 11:00–20:00, обед 14:00–15:00
INSERT INTO working_hours (master_id, dow, start_time, end_time)
SELECT 2, d, '11:00', '20:00' FROM generate_series(1, 5) d;
INSERT INTO breaks (master_id, dow, start_time, end_time)
SELECT 2, d, '14:00', '15:00' FROM generate_series(1, 5) d;

SELECT setval('salons_id_seq', 1), setval('masters_id_seq', 2),
       setval('service_categories_id_seq', 3), setval('services_id_seq', 4);
