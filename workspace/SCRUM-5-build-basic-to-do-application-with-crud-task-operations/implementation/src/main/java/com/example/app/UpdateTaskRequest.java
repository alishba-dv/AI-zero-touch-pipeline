package com.example.app;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

// Unknown fields (e.g. id, createdAt) in the request body are silently dropped.
@JsonIgnoreProperties(ignoreUnknown = true)
public class UpdateTaskRequest {
    private String title;
    private String description;
    private String status;

    public boolean hasAnyField() {
        return title != null || description != null || status != null;
    }

    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }

    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
}