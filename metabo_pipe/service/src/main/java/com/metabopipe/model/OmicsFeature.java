package com.metabopipe.model;

import jakarta.persistence.*;

@Entity
@Table(name = "omics_feature")
public class OmicsFeature {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "feature_name", nullable = false)
    private String featureName;

    @Enumerated(EnumType.STRING)
    @Column(name = "omics_type", nullable = false)
    private OmicsType omicsType;

    protected OmicsFeature() {}

    public OmicsFeature(String featureName, OmicsType omicsType) {
        this.featureName = featureName;
        this.omicsType = omicsType;
    }

    public Long getId()             { return id; }
    public String getFeatureName()  { return featureName; }
    public OmicsType getOmicsType() { return omicsType; }
}
