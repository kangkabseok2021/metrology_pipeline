package com.metabopipe.repository;

import com.metabopipe.model.Sample;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface SampleRepository extends JpaRepository<Sample, Long> {
    Optional<Sample> findBySampleId(String sampleId);
}
