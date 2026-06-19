package com.metabopipe;

import com.metabopipe.model.OmicsType;
import com.metabopipe.service.CorrelationNetworkService;
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
class CorrelationNetworkServiceTest {

    @Container
    @ServiceConnection
    static PostgreSQLContainer<?> postgres =
            new PostgreSQLContainer<>("postgres:16-alpine");

    @Autowired
    OmicsImportService importService;

    @Autowired
    CorrelationNetworkService networkService;

    @Test
    void correlationPValue_perfectLinearData_isSmall() {
        // n=10, r=1.0 → t → infinity → p ≈ 0
        double p = CorrelationNetworkService.correlationPValue(0.999, 10);
        assertThat(p).isLessThan(0.001);
    }

    @Test
    void correlationPValue_zeroCor_isLarge() {
        double p = CorrelationNetworkService.correlationPValue(0.0, 10);
        assertThat(p).isEqualTo(1.0);
    }

    @Test
    void computeNetwork_detectsHighCorrelation() throws Exception {
        // 4 samples: metabolomics glucose and transcriptomics gene1 perfectly correlated
        String metCsv =
                "sample_id,sample_group,feature_name,value\n" +
                "SA,groupA,glucose,10.0\n" +
                "SB,groupA,glucose,20.0\n" +
                "SC,groupA,glucose,30.0\n" +
                "SD,groupA,glucose,40.0\n";

        String txCsv =
                "sample_id,sample_group,feature_name,value\n" +
                "SA,groupA,gene1,1.0\n" +
                "SB,groupA,gene1,2.0\n" +
                "SC,groupA,gene1,3.0\n" +
                "SD,groupA,gene1,4.0\n";

        importService.importCsv(new StringReader(metCsv), OmicsType.METABOLOMICS);
        importService.importCsv(new StringReader(txCsv), OmicsType.TRANSCRIPTOMICS);

        int edges = networkService.computeNetwork("groupA", 0.7, 0.05);
        assertThat(edges).isGreaterThanOrEqualTo(1);
    }

    @Test
    void getNetwork_returnsNodeEdgeStructure() throws Exception {
        // Uses data from previous test (same Testcontainers instance per class, no @DirtiesContext)
        var network = networkService.getNetwork("groupA");
        assertThat(network).isNotNull();
        assertThat(network.nodes()).isNotNull();
        assertThat(network.edges()).isNotNull();
    }
}
