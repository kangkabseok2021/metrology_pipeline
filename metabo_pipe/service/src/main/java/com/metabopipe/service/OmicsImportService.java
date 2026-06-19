package com.metabopipe.service;

import com.metabopipe.model.*;
import com.metabopipe.repository.*;
import com.opencsv.CSVReader;
import com.opencsv.exceptions.CsvValidationException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.IOException;
import java.io.Reader;
import java.util.ArrayList;
import java.util.List;

@Service
public class OmicsImportService {

    private final SampleRepository sampleRepo;
    private final OmicsFeatureRepository featureRepo;
    private final OmicsFeatureValueRepository valueRepo;

    public OmicsImportService(SampleRepository sampleRepo,
                               OmicsFeatureRepository featureRepo,
                               OmicsFeatureValueRepository valueRepo) {
        this.sampleRepo = sampleRepo;
        this.featureRepo = featureRepo;
        this.valueRepo = valueRepo;
    }

    /**
     * Import a CSV with columns: sample_id, sample_group, feature_name, value.
     * Idempotent: existing (sample, feature) pairs are skipped.
     */
    @Transactional
    public int importCsv(Reader csvReader, OmicsType omicsType)
            throws IOException, CsvValidationException {

        int imported = 0;
        try (CSVReader csv = new CSVReader(csvReader)) {
            String[] header = csv.readNext();
            if (header == null) return 0;

            String[] row;
            while ((row = csv.readNext()) != null) {
                if (row.length < 4) continue;
                String sampleId    = row[0].trim();
                String sampleGroup = row[1].trim();
                String featureName = row[2].trim();
                double value       = Double.parseDouble(row[3].trim());

                Sample sample = sampleRepo.findBySampleId(sampleId)
                        .orElseGet(() -> sampleRepo.save(new Sample(sampleId, sampleGroup)));

                OmicsFeature feature = featureRepo
                        .findByFeatureNameAndOmicsType(featureName, omicsType)
                        .orElseGet(() -> featureRepo.save(new OmicsFeature(featureName, omicsType)));

                if (!valueRepo.existsBySampleAndFeature(sample, feature)) {
                    valueRepo.save(new OmicsFeatureValue(sample, feature, value));
                    imported++;
                }
            }
        }
        return imported;
    }

    public List<OmicsFeature> listFeatures() {
        return featureRepo.findAll();
    }
}
