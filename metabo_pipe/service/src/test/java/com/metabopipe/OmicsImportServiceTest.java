package com.metabopipe;

import com.metabopipe.model.OmicsType;
import com.metabopipe.service.OmicsImportService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.io.StringReader;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@Testcontainers
class OmicsImportServiceTest {

    @Container
    @ServiceConnection
    static PostgreSQLContainer<?> postgres =
            new PostgreSQLContainer<>("postgres:16-alpine");

    @Autowired
    OmicsImportService importService;

    private static final String CSV =
            "sample_id,sample_group,feature_name,value\n" +
            "S1,control,glucose,1234.5\n" +
            "S1,control,alanine,567.8\n" +
            "S2,treatment,glucose,2345.6\n" +
            "S2,treatment,alanine,890.1\n";

    @Test
    void importCsv_persistsCorrectCount() throws Exception {
        int count = importService.importCsv(new StringReader(CSV), OmicsType.METABOLOMICS);
        assertThat(count).isEqualTo(4);
    }

    @Test
    void importCsv_idempotentOnDuplicates() throws Exception {
        importService.importCsv(new StringReader(CSV), OmicsType.METABOLOMICS);
        int second = importService.importCsv(new StringReader(CSV), OmicsType.METABOLOMICS);
        assertThat(second).isEqualTo(0);
    }

    @Test
    void listFeatures_returnsImportedFeatures() throws Exception {
        importService.importCsv(new StringReader(CSV), OmicsType.METABOLOMICS);
        var features = importService.listFeatures();
        assertThat(features).extracting("featureName")
                .contains("glucose", "alanine");
    }
}
