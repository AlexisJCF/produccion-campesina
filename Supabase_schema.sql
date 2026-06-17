-- Tablas para COOPROGRESO
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE survey_registry (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  registration_date DATE NOT NULL,
  type TEXT CHECK (type IN ('INICIAL','ACTUAL')),
  reason TEXT,
  signature BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE family_members (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  survey_id UUID REFERENCES survey_registry(id) ON DELETE CASCADE,
  is_main BOOLEAN DEFAULT FALSE,
  nombres TEXT,
  apellidos TEXT,
  parentesco TEXT,
  birth_date DATE,
  id_number TEXT,
  id_issue_place TEXT,
  phone TEXT,
  email TEXT,
  education_level TEXT,
  discipline TEXT,
  occupation TEXT,
  sisben_id TEXT,
  sisben_category TEXT
);

CREATE TABLE housing (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  survey_id UUID REFERENCES survey_registry(id) ON DELETE CASCADE,
  property_type TEXT,
  location TEXT,
  cadastral_id TEXT,
  built_area_m2 FLOAT,
  patio_area_m2 FLOAT,
  water_quality TEXT,
  energy_quality TEXT,
  internet_quality TEXT,
  sewage TEXT,
  waste_management TEXT
);

CREATE TABLE land (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  survey_id UUID REFERENCES survey_registry(id) ON DELETE CASCADE,
  property_type TEXT,
  land_name TEXT,
  location TEXT,
  cadastral_id TEXT,
  total_area_m2 FLOAT,
  land_type TEXT,
  is_floodable BOOLEAN,
  water_quality TEXT,
  slope_degree TEXT,
  energy_quality TEXT,
  internet_quality TEXT,
  sewage TEXT,
  waste_management TEXT,
  real_estate_registration TEXT
);

CREATE TABLE production_capacity (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  survey_id UUID REFERENCES survey_registry(id) ON DELETE CASCADE,
  product_name TEXT,
  measure_unit TEXT,
  occupied_area_m2 FLOAT,
  start_date DATE,
  production_date DATE,
  frequency TEXT,
  quantity_produced FLOAT,
  total_price DECIMAL,
  unit_price DECIMAL,
  product_quality TEXT
);

CREATE TABLE service_capacity (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  survey_id UUID REFERENCES survey_registry(id) ON DELETE CASCADE,
  service_name TEXT,
  measure_unit TEXT,
  occupied_area_m2 FLOAT,
  season_start DATE,
  season_end DATE,
  frequency TEXT,
  quantity FLOAT,
  price DECIMAL,
  service_quality TEXT
);