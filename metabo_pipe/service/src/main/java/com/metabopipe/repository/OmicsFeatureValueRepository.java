package com.metabopipe.repository;

import com.metabopipe.model.OmicsFeature;
import com.metabopipe.model.OmicsFeatureValue;
import com.metabopipe.model.Sample;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.List;

public interface OmicsFeatureValueRepository extends JpaRepository<OmicsFeatureValue, Long> {
    List<OmicsFeatureValue> findByFeature(OmicsFeature feature);

    @Query("SELECT v FROM OmicsFeatureValue v WHERE v.sample.sampleGroup = :sampleGroup")
    List<OmicsFeatureValue> findBySampleGroup(String sampleGroup);

    boolean existsBySampleAndFeature(Sample sample, OmicsFeature feature);
}
