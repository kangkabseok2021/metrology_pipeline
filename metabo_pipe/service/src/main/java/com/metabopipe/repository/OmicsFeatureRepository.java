package com.metabopipe.repository;

import com.metabopipe.model.OmicsFeature;
import com.metabopipe.model.OmicsType;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface OmicsFeatureRepository extends JpaRepository<OmicsFeature, Long> {
    Optional<OmicsFeature> findByFeatureNameAndOmicsType(String featureName, OmicsType omicsType);
    List<OmicsFeature> findByOmicsType(OmicsType omicsType);
}
