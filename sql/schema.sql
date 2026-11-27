DROP TABLE IF EXISTS recommendations;
DROP TABLE IF EXISTS vehicles;
DROP TABLE IF EXISTS oils;
DROP TABLE IF EXISTS oil_brands;

CREATE TABLE oil_brands (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE oils (
    id SERIAL PRIMARY KEY,
    brand_id INTEGER NOT NULL REFERENCES oil_brands(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    sae_viscosity TEXT,
    oil_type TEXT,
    UNIQUE (brand_id, name)
);

CREATE TABLE vehicles (
    id SERIAL PRIMARY KEY,
    make TEXT NOT NULL,
    model TEXT NOT NULL,
    engine TEXT,
    year_from INTEGER,
    year_to INTEGER,
    UNIQUE (make, model, engine, year_from, year_to)
);

CREATE TABLE recommendations (
    id SERIAL PRIMARY KEY,
    vehicle_id INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    oil_id INTEGER NOT NULL REFERENCES oils(id) ON DELETE CASCADE,
    capacity_liters NUMERIC(5, 2),
    source_pdf TEXT,
    notes TEXT,
    UNIQUE (vehicle_id, oil_id, capacity_liters, source_pdf, notes)
);

CREATE INDEX idx_vehicles_make_model ON vehicles (make, model);
CREATE INDEX idx_recommendations_vehicle ON recommendations (vehicle_id);
