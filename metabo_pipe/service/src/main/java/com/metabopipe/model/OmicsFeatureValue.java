package com.metabopipe.model;

import jakarta.persistence.*;

@Entity
@Table(
    name = "omics_feature_value",
    uniqueConstraints = @UniqueConstraint(columnNames = {"sample_id", "feature_id"})
)
public class OmicsFeatureValue {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "sample_id", nullable = false)
    private Sample sample;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "feature_id", nullable = false)
    private OmicsFeature feature;

    @Column(nullable = false)
    private double value;

    protected OmicsFeatureValue() {}

    public OmicsFeatureValue(Sample sample, OmicsFeature feature, double value) {
        this.sample = sample;
        this.feature = feature;
        this.value = value;
    }

    public Long getId()           { return id; }
    public Sample getSample()     { return sample; }
    public OmicsFeature getFeature() { return feature; }
    public double getValue()      { return value; }
}
