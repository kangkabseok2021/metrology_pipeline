CREATE TABLE sample (
    id           BIGSERIAL PRIMARY KEY,
    sample_id    VARCHAR(255) NOT NULL UNIQUE,
    sample_group VARCHAR(255) NOT NULL
);

CREATE TABLE omics_feature (
    id           BIGSERIAL PRIMARY KEY,
    feature_name VARCHAR(255) NOT NULL,
    omics_type   VARCHAR(50)  NOT NULL
);

CREATE TABLE omics_feature_value (
    id         BIGSERIAL PRIMARY KEY,
    sample_id  BIGINT NOT NULL REFERENCES sample(id) ON DELETE CASCADE,
    feature_id BIGINT NOT NULL REFERENCES omics_feature(id) ON DELETE CASCADE,
    value      DOUBLE PRECISION NOT NULL,
    UNIQUE (sample_id, feature_id)
);
CREATE INDEX idx_ofv_sample_feature ON omics_feature_value(sample_id, feature_id);

CREATE TABLE network_edge (
    id                BIGSERIAL PRIMARY KEY,
    source_feature_id BIGINT REFERENCES omics_feature(id) ON DELETE CASCADE,
    target_feature_id BIGINT REFERENCES omics_feature(id) ON DELETE CASCADE,
    correlation       DOUBLE PRECISION NOT NULL,
    p_value           DOUBLE PRECISION NOT NULL,
    sample_group      VARCHAR(255) NOT NULL
);
