package com.metabopipe.repository;

import com.metabopipe.model.NetworkEdge;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface NetworkEdgeRepository extends JpaRepository<NetworkEdge, Long> {
    List<NetworkEdge> findBySampleGroup(String sampleGroup);
}
