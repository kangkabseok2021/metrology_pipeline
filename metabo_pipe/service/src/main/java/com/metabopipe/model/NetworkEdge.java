package com.metabopipe.model;

import jakarta.persistence.*;

@Entity
@Table(name = "network_edge")
public class NetworkEdge {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "source_feature_id")
    private OmicsFeature sourceFeature;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "target_feature_id")
    private OmicsFeature targetFeature;

    @Column(nullable = false)
    private double correlation;

    @Column(name = "p_value", nullable = false)
    private double pValue;

    @Column(name = "sample_group", nullable = false)
    private String sampleGroup;

    protected NetworkEdge() {}

    public NetworkEdge(OmicsFeature source, OmicsFeature target,
                       double correlation, double pValue, String sampleGroup) {
        this.sourceFeature = source;
        this.targetFeature = target;
        this.correlation = correlation;
        this.pValue = pValue;
        this.sampleGroup = sampleGroup;
    }

    public Long getId()                    { return id; }
    public OmicsFeature getSourceFeature() { return sourceFeature; }
    public OmicsFeature getTargetFeature() { return targetFeature; }
    public double getCorrelation()         { return correlation; }
    public double getPValue()              { return pValue; }
    public String getSampleGroup()         { return sampleGroup; }
}
