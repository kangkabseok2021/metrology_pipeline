package com.metabopipe.controller;

import com.metabopipe.service.CorrelationNetworkService;
import com.metabopipe.service.CorrelationNetworkService.NetworkDto;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/network")
public class NetworkController {

    private final CorrelationNetworkService networkService;

    public NetworkController(CorrelationNetworkService networkService) {
        this.networkService = networkService;
    }

    @PostMapping("/{sampleGroup}/compute")
    public ResponseEntity<String> compute(
            @PathVariable String sampleGroup,
            @RequestParam(defaultValue = "0.7") double rThreshold,
            @RequestParam(defaultValue = "0.05") double pThreshold) {

        int edges = networkService.computeNetwork(sampleGroup, rThreshold, pThreshold);
        return ResponseEntity.ok("Computed " + edges + " edges for group: " + sampleGroup);
    }

    @GetMapping("/{sampleGroup}")
    public ResponseEntity<NetworkDto> getNetwork(@PathVariable String sampleGroup) {
        return ResponseEntity.ok(networkService.getNetwork(sampleGroup));
    }
}
