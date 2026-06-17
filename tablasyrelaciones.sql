-- Tabla principal que agrupa cada levantamiento (visita o actualización)
survey_registry (
  id UUID PK,
  registration_date DATE,
  type TEXT CHECK (type IN ('INICIAL','ACTUAL')),
  reason TEXT,
  signature BOOLEAN,
  created_at TIMESTAMP
)

-- Miembros de la familia (incluye al productor principal)
family_members (
  id UUID PK,
  survey_id UUID FK → survey_registry(id),
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
)

-- Datos de la vivienda (1 por registro)
housing (
  id UUID PK,
  survey_id UUID FK → survey_registry(id),
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
)

-- Datos del predio (1 por registro)
land (
  id UUID PK,
  survey_id UUID FK → survey_registry(id),
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
)

-- Capacidad de producción de bienes (varios por registro)
production_capacity (
  id UUID PK,
  survey_id UUID FK → survey_registry(id),
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
)

-- Capacidad de prestación de servicios (varios por registro)
service_capacity (
  id UUID PK,
  survey_id UUID FK → survey_registry(id),
  service_name TEXT,
  measure_unit TEXT,
  occupied_area_m2 FLOAT,
  season_start DATE,
  season_end DATE,
  frequency TEXT,
  quantity FLOAT,
  price DECIMAL,
  service_quality TEXT
)