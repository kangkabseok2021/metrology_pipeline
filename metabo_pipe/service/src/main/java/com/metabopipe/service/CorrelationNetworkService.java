package com.metabopipe.service;

import com.metabopipe.model.*;
import com.metabopipe.repository.*;
import org.apache.commons.math3.distribution.TDistribution;
import org.apache.commons.math3.stat.correlation.PearsonsCorrelation;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.util.stream.Collectors;

@Service
public class CorrelationNetworkService {

    private final OmicsFeatureRepository featureRepo;
    private final OmicsFeatureValueRepository valueRepo;
    private final NetworkEdgeRepository edgeRepo;

    public CorrelationNetworkService(OmicsFeatureRepository featureRepo,
                                      OmicsFeatureValueRepository valueRepo,
                                      NetworkEdgeRepository edgeRepo) {
        this.featureRepo = featureRepo;
        this.valueRepo = valueRepo;
        this.edgeRepo = edgeRepo;
    }

    /**
     * Compute pairwise Pearson correlations between METABOLOMICS and TRANSCRIPTOMICS/PROTEOMICS
     * features for a sample group, persisting edges above the |r| threshold.
     */
    @Transactional
    public int computeNetwork(String sampleGroup, double rThreshold, double pThreshold) {
        List<OmicsFeatureValue> groupValues = valueRepo.findBySampleGroup(sampleGroup);
        if (groupValues.isEmpty()) return 0;

        // Collect unique samples and features
        List<String> samples = groupValues.stream()
                .map(v -> v.getSample().getSampleId())
                .distinct().sorted().toList();

        List<OmicsFeature> metFeatures = featureRepo.findByOmicsType(OmicsType.METABOLOMICS);
        List<OmicsFeature> otherFeatures = new ArrayList<>();
        otherFeatures.addAll(featureRepo.findByOmicsType(OmicsType.TRANSCRIPTOMICS));
        otherFeatures.addAll(featureRepo.findByOmicsType(OmicsType.PROTEOMICS));

        if (metFeatures.isEmpty() || otherFeatures.isEmpty()) return 0;

        // Build value lookup: featureId -> sampleId -> value
        Map<Long, Map<String, Double>> valueLookup = new HashMap<>();
        for (OmicsFeatureValue v : groupValues) {
            valueLookup
                .computeIfAbsent(v.getFeature().getId(), k -> new HashMap<>())
                .put(v.getSample().getSampleId(), v.getValue());
        }

        int edgesAdded = 0;
        PearsonsCorrelation pearson = new PearsonsCorrelation();

        for (OmicsFeature mf : metFeatures) {
            double[] xArr = toArray(samples, valueLookup.getOrDefault(mf.getId(), Map.of()));
            if (xArr == null) continue;

            for (OmicsFeature of : otherFeatures) {
                double[] yArr = toArray(samples, valueLookup.getOrDefault(of.getId(), Map.of()));
                if (yArr == null) continue;

                double r = pearson.correlation(xArr, yArr);
                if (Double.isNaN(r)) continue;

                double p = correlationPValue(r, xArr.length);
                if (Math.abs(r) >= rThreshold && p <= pThreshold) {
                    edgeRepo.save(new NetworkEdge(mf, of, r, p, sampleGroup));
                    edgesAdded++;
                }
            }
        }
        return edgesAdded;
    }

    public record NodeDto(Long id, String featureName, String omicsType) {}
    public record EdgeDto(Long sourceId, Long targetId, double correlation, double pValue) {}
    public record NetworkDto(List<NodeDto> nodes, List<EdgeDto> edges) {}

    public NetworkDto getNetwork(String sampleGroup) {
        List<NetworkEdge> edges = edgeRepo.findBySampleGroup(sampleGroup);
        Set<OmicsFeature> featureSet = new LinkedHashSet<>();
        for (NetworkEdge e : edges) {
            featureSet.add(e.getSourceFeature());
            featureSet.add(e.getTargetFeature());
        }
        List<NodeDto> nodes = featureSet.stream()
                .map(f -> new NodeDto(f.getId(), f.getFeatureName(), f.getOmicsType().name()))
                .toList();
        List<EdgeDto> edgeDtos = edges.stream()
                .map(e -> new EdgeDto(
                        e.getSourceFeature().getId(),
                        e.getTargetFeature().getId(),
                        e.getCorrelation(),
                        e.getPValue()))
                .toList();
        return new NetworkDto(nodes, edgeDtos);
    }

    // -----------------------------------------------------------------------

    private static double[] toArray(List<String> samples, Map<String, Double> lookup) {
        if (lookup.size() < samples.size()) return null;
        double[] arr = new double[samples.size()];
        for (int i = 0; i < samples.size(); i++) {
            Double v = lookup.get(samples.get(i));
            if (v == null) return null;
            arr[i] = v;
        }
        return arr;
    }

    public static double correlationPValue(double r, int n) {
        if (n <= 2) return 1.0;
        double t = r * Math.sqrt(n - 2) / Math.sqrt(1 - r * r + 1e-300);
        TDistribution dist = new TDistribution(n - 2);
        return 2.0 * (1.0 - dist.cumulativeProbability(Math.abs(t)));
    }
}
