package com.metabopipe.model;

import jakarta.persistence.*;

@Entity
@Table(name = "sample")
public class Sample {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "sample_id", nullable = false, unique = true)
    private String sampleId;

    @Column(name = "sample_group", nullable = false)
    private String sampleGroup;

    protected Sample() {}

    public Sample(String sampleId, String sampleGroup) {
        this.sampleId = sampleId;
        this.sampleGroup = sampleGroup;
    }

    public Long getId()            { return id; }
    public String getSampleId()    { return sampleId; }
    public String getSampleGroup() { return sampleGroup; }
}
