package com.metabopipe.controller;

import com.metabopipe.model.OmicsFeature;
import com.metabopipe.model.OmicsType;
import com.metabopipe.service.OmicsImportService;
import com.opencsv.exceptions.CsvValidationException;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class OmicsImportController {

    private final OmicsImportService importService;

    public OmicsImportController(OmicsImportService importService) {
        this.importService = importService;
    }

    @PostMapping("/import/{omicsType}")
    public ResponseEntity<Map<String, Object>> importCsv(
            @PathVariable String omicsType,
            @RequestParam("file") MultipartFile file) throws IOException, CsvValidationException {

        OmicsType type = OmicsType.valueOf(omicsType.toUpperCase());
        int count = importService.importCsv(
                new InputStreamReader(file.getInputStream(), StandardCharsets.UTF_8), type);
        return ResponseEntity.ok(Map.of("imported", count, "omicsType", type.name()));
    }

    @GetMapping("/features")
    public ResponseEntity<List<OmicsFeature>> listFeatures() {
        return ResponseEntity.ok(importService.listFeatures());
    }
}
