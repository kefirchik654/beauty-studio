-- Схема PostgreSQL 14+ для бота записи (MVP, один набор таблиц на все салоны).
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE salons (
    id                   serial PRIMARY KEY,
    name                 text NOT NULL,
    tz                   text NOT NULL DEFAULT 'Asia/Krasnoyarsk',
    greeting             text NOT NULL DEFAULT 'Здесь вы можете записаться на услуги за несколько шагов.',
    address              text NOT NULL DEFAULT '',
    phone                text NOT NULL DEFAULT '',
    hours_text           text NOT NULL DEFAULT '',
    map_url              text,
    min_lead_minutes     int  NOT NULL DEFAULT 60,    -- минимальное время до записи
    slot_step_minutes    int  NOT NULL DEFAULT 30,    -- шаг сетки времени
    booking_horizon_days int  NOT NULL DEFAULT 60,
    cancel_before_hours  int  NOT NULL DEFAULT 2,     -- самостоятельная отмена не позже чем за N часов
    require_phone        boolean NOT NULL DEFAULT false,
    is_active            boolean NOT NULL DEFAULT true
);

CREATE TABLE masters (
    id               serial PRIMARY KEY,
    salon_id         int NOT NULL REFERENCES salons(id) ON DELETE CASCADE,
    name             text NOT NULL,
    specialization   text NOT NULL DEFAULT '',
    experience_years int,
    bio              text NOT NULL DEFAULT '',
    photo_file_id    text,
    is_active        boolean NOT NULL DEFAULT true
);

CREATE TABLE service_categories (
    id       serial PRIMARY KEY,
    salon_id int NOT NULL REFERENCES salons(id) ON DELETE CASCADE,
    name     text NOT NULL,
    sort     int NOT NULL DEFAULT 0
);

CREATE TABLE services (
    id          serial PRIMARY KEY,
    salon_id    int NOT NULL REFERENCES salons(id) ON DELETE CASCADE,
    category_id int REFERENCES service_categories(id) ON DELETE SET NULL,
    name        text NOT NULL,
    description text NOT NULL DEFAULT '',
    price       int  NOT NULL,                 -- в рублях
    price_from  boolean NOT NULL DEFAULT false, -- «от»
    duration_min int NOT NULL CHECK (duration_min > 0),
    buffer_min   int NOT NULL DEFAULT 0,
    is_active   boolean NOT NULL DEFAULT true
);

CREATE TABLE master_services (
    master_id      int NOT NULL REFERENCES masters(id) ON DELETE CASCADE,
    service_id     int NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    price_override int,
    PRIMARY KEY (master_id, service_id)
);

-- dow: 0 = понедельник ... 6 = воскресенье (как в Python date.weekday())
CREATE TABLE working_hours (
    id         serial PRIMARY KEY,
    master_id  int NOT NULL REFERENCES masters(id) ON DELETE CASCADE,
    dow        smallint NOT NULL CHECK (dow BETWEEN 0 AND 6),
    start_time time NOT NULL,
    end_time   time NOT NULL CHECK (end_time > start_time)
);

CREATE TABLE breaks (
    id         serial PRIMARY KEY,
    master_id  int NOT NULL REFERENCES masters(id) ON DELETE CASCADE,
    dow        smallint NOT NULL CHECK (dow BETWEEN 0 AND 6),
    start_time time NOT NULL,
    end_time   time NOT NULL CHECK (end_time > start_time)
);

-- Исключения: выходной, отпуск или особые часы на период дат
CREATE TABLE schedule_exceptions (
    id         serial PRIMARY KEY,
    master_id  int NOT NULL REFERENCES masters(id) ON DELETE CASCADE,
    date_from  date NOT NULL,
    date_to    date NOT NULL CHECK (date_to >= date_from),
    kind       text NOT NULL CHECK (kind IN ('day_off', 'vacation', 'custom_hours')),
    start_time time,
    end_time   time
);

CREATE TABLE clients (
    id          serial PRIMARY KEY,
    salon_id    int NOT NULL REFERENCES salons(id) ON DELETE CASCADE,
    telegram_id bigint NOT NULL,
    name        text NOT NULL DEFAULT '',
    phone       text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (salon_id, telegram_id)
);

CREATE TABLE appointments (
    id           serial PRIMARY KEY,
    salon_id     int NOT NULL REFERENCES salons(id) ON DELETE CASCADE,
    client_id    int NOT NULL REFERENCES clients(id),
    master_id    int NOT NULL REFERENCES masters(id),
    service_id   int NOT NULL REFERENCES services(id),
    service_name text NOT NULL,          -- снимок на момент записи
    price        int  NOT NULL,          -- снимок на момент записи
    starts_at    timestamptz NOT NULL,
    ends_at      timestamptz NOT NULL,   -- начало + длительность услуги
    busy_until   timestamptz NOT NULL,   -- ends_at + буфер после услуги
    status       text NOT NULL DEFAULT 'booked'
                 CHECK (status IN ('booked','confirmed','completed','no_show',
                                   'cancelled_by_client','cancelled_by_salon','rescheduled')),
    created_at   timestamptz NOT NULL DEFAULT now(),
    CHECK (busy_until >= ends_at AND ends_at > starts_at),
    -- Главная защита: у одного мастера активные записи не могут пересекаться
    EXCLUDE USING gist (
        master_id WITH =,
        tstzrange(starts_at, busy_until, '[)') WITH &&
    ) WHERE (status IN ('booked', 'confirmed'))
);

CREATE INDEX ON appointments (master_id, starts_at);
CREATE INDEX ON appointments (client_id, starts_at);
CREATE INDEX ON working_hours (master_id, dow);
CREATE INDEX ON schedule_exceptions (master_id, date_from, date_to);
