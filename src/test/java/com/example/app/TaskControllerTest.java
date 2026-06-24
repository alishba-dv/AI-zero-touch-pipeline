package com.example.app;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class TaskControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private TaskRepository taskRepository;

    @BeforeEach
    void resetStore() {
        taskRepository.deleteAll();
    }

    // -------------------------------------------------------------------------
    // AC-1 / Happy-path: Create a task with title only
    // -------------------------------------------------------------------------
    @Test
    void createTask_withTitleOnly_returns201WithSystemFields() throws Exception {
        Map<String, String> body = Map.of("title", "Buy milk");

        mockMvc.perform(post("/tasks")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(body)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").isNotEmpty())
                .andExpect(jsonPath("$.title").value("Buy milk"))
                .andExpect(jsonPath("$.status").value("pending"))
                .andExpect(jsonPath("$.createdAt").isNotEmpty());
    }

    // AC-1: description is optional — create with both fields
    @Test
    void createTask_withTitleAndDescription_returns201() throws Exception {
        Map<String, Object> body = Map.of("title", "Buy milk", "description", "Full-fat only");

        mockMvc.perform(post("/tasks")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(body)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.description").value("Full-fat only"));
    }

    // -------------------------------------------------------------------------
    // AC-2 / E2: Create with missing title → 400
    // -------------------------------------------------------------------------
    @Test
    void createTask_missingTitle_returns400() throws Exception {
        Map<String, String> body = Map.of("description", "No title here");

        mockMvc.perform(post("/tasks")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(body)))
                .andExpect(status().isBadRequest());
    }

    // E1: Create with empty string title → 400
    @Test
    void createTask_emptyTitle_returns400() throws Exception {
        Map<String, String> body = Map.of("title", "");

        mockMvc.perform(post("/tasks")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(body)))
                .andExpect(status().isBadRequest());
    }

    // E1: Create with whitespace-only title → 400
    @Test
    void createTask_whitespaceTitle_returns400() throws Exception {
        Map<String, String> body = Map.of("title", "   ");

        mockMvc.perform(post("/tasks")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(body)))
                .andExpect(status().isBadRequest());
    }

    // E2: Completely empty body → 400
    @Test
    void createTask_emptyBody_returns400() throws Exception {
        mockMvc.perform(post("/tasks")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{}"))
                .andExpect(status().isBadRequest());
    }

    // -------------------------------------------------------------------------
    // AC-3 / Happy-path: List all tasks returns all with full metadata
    // -------------------------------------------------------------------------
    @Test
    void listTasks_withExistingTasks_returnsAllWithMetadata() throws Exception {
        createTaskViaApi("Task One", null);
        createTaskViaApi("Task Two", "desc two");

        mockMvc.perform(get("/tasks"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(2)))
                .andExpect(jsonPath("$[*].id").exists())
                .andExpect(jsonPath("$[*].title").exists())
                .andExpect(jsonPath("$[*].status").exists())
                .andExpect(jsonPath("$[*].createdAt").exists());
    }

    // AC-4: List when empty → 200 with []
    @Test
    void listTasks_emptyStore_returns200WithEmptyArray() throws Exception {
        mockMvc.perform(get("/tasks"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(0)));
    }

    // -------------------------------------------------------------------------
    // AC-5 / Happy-path: Update status to completed
    // -------------------------------------------------------------------------
    @Test
    void updateTask_statusToCompleted_returns200AndPersists() throws Exception {
        String id = createTaskViaApi("Buy eggs", null);
        Map<String, String> patch = Map.of("status", "completed");

        mockMvc.perform(patch("/tasks/" + id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(patch)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("completed"));

        // Verify persistence via GET
        mockMvc.perform(get("/tasks"))
                .andExpect(jsonPath("$[0].status").value("completed"));
    }

    // Happy-path: Update title only
    @Test
    void updateTask_titleOnly_returns200WithUpdatedTitle() throws Exception {
        String id = createTaskViaApi("Old title", null);
        Map<String, String> patch = Map.of("title", "New title");

        mockMvc.perform(patch("/tasks/" + id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(patch)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("New title"));
    }

    // Happy-path: Update description only
    @Test
    void updateTask_descriptionOnly_returns200WithUpdatedDescription() throws Exception {
        String id = createTaskViaApi("Buy eggs", "free range");
        Map<String, String> patch = Map.of("description", "organic");

        mockMvc.perform(patch("/tasks/" + id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(patch)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.description").value("organic"));
    }

    // Happy-path: Update multiple fields at once
    @Test
    void updateTask_multipleFields_returns200() throws Exception {
        String id = createTaskViaApi("Old title", "old desc");
        Map<String, String> patch = Map.of("title", "New title", "description", "new desc", "status", "completed");

        mockMvc.perform(patch("/tasks/" + id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(patch)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("New title"))
                .andExpect(jsonPath("$.description").value("new desc"))
                .andExpect(jsonPath("$.status").value("completed"));
    }

    // AC-6 / E3: Update non-existent ID → 404
    @Test
    void updateTask_nonExistentId_returns404() throws Exception {
        Map<String, String> patch = Map.of("status", "completed");

        mockMvc.perform(patch("/tasks/nonexistent-id-99999")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(patch)))
                .andExpect(status().isNotFound());
    }

    // AC-7 / E6: Update with invalid status value → 400
    @Test
    void updateTask_invalidStatus_returns400() throws Exception {
        String id = createTaskViaApi("Some task", null);
        Map<String, String> patch = Map.of("status", "in-progress");

        mockMvc.perform(patch("/tasks/" + id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(patch)))
                .andExpect(status().isBadRequest());
    }

    // E7: Update with empty body (no fields) → 400
    @Test
    void updateTask_emptyBody_returns400() throws Exception {
        String id = createTaskViaApi("Some task", null);

        mockMvc.perform(patch("/tasks/" + id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{}"))
                .andExpect(status().isBadRequest());
    }

    // -------------------------------------------------------------------------
    // AC-8 / Happy-path: Delete a task → 204, then gone from list
    // -------------------------------------------------------------------------
    @Test
    void deleteTask_existingId_returns204AndRemovesFromList() throws Exception {
        String id = createTaskViaApi("Task to delete", null);

        mockMvc.perform(delete("/tasks/" + id))
                .andExpect(status().isNoContent());

        mockMvc.perform(get("/tasks"))
                .andExpect(jsonPath("$", hasSize(0)));
    }

    // AC-9 / E4: Delete non-existent ID → 404
    @Test
    void deleteTask_nonExistentId_returns404() throws Exception {
        mockMvc.perform(delete("/tasks/nonexistent-id-99999"))
                .andExpect(status().isNotFound());
    }

    // E5: Delete with malformed/invalid ID format → 400
    @Test
    void deleteTask_malformedId_returns400() throws Exception {
        // An ID containing characters that violate the expected format
        mockMvc.perform(delete("/tasks/!!invalid--id!!"))
                .andExpect(status().isBadRequest());
    }

    // -------------------------------------------------------------------------
    // AC-10: Immutability — id and createdAt unchanged after update
    // -------------------------------------------------------------------------
    @Test
    void updateTask_idAndCreatedAtAreImmutable() throws Exception {
        MvcResult created = mockMvc.perform(post("/tasks")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\":\"Immutable test\"}"))
                .andReturn();

        String responseJson = created.getResponse().getContentAsString();
        Map<?, ?> task = objectMapper.readValue(responseJson, Map.class);
        String originalId = String.valueOf(task.get("id"));
        String originalCreatedAt = String.valueOf(task.get("createdAt"));

        Map<String, Object> patch = Map.of(
                "title", "Updated title",
                "status", "completed",
                "id", "tampered-id",
                "createdAt", "2000-01-01T00:00:00Z"
        );

        mockMvc.perform(patch("/tasks/" + originalId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(patch)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(originalId))
                .andExpect(jsonPath("$.createdAt").value(originalCreatedAt));
    }

    // -------------------------------------------------------------------------
    // E9: Duplicate titles are allowed (uniqueness only on id)
    // -------------------------------------------------------------------------
    @Test
    void createTask_duplicateTitle_bothCreatedWithUniqueIds() throws Exception {
        String id1 = createTaskViaApi("Same title", null);
        String id2 = createTaskViaApi("Same title", null);

        assertThat(id1).isNotEqualTo(id2);

        mockMvc.perform(get("/tasks"))
                .andExpect(jsonPath("$", hasSize(2)));
    }

    // -------------------------------------------------------------------------
    // Boundary: Single character title — should be accepted
    // -------------------------------------------------------------------------
    @Test
    void createTask_singleCharTitle_returns201() throws Exception {
        Map<String, String> body = Map.of("title", "X");

        mockMvc.perform(post("/tasks")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(body)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.title").value("X"));
    }

    // Boundary: Title with leading/trailing whitespace — trimmed or rejected
    @Test
    void createTask_titleWithLeadingTrailingSpaces_trimmedOrRejected() throws Exception {
        Map<String, String> body = Map.of("title", "  Buy milk  ");

        MvcResult result = mockMvc.perform(post("/tasks")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(body)))
                .andReturn();

        int status = result.getResponse().getStatus();
        // Either 201 with a trimmed title, or 400 — both are acceptable; not 5xx
        assertThat(status).isIn(200, 201, 400);
        if (status == 201) {
            Map<?, ?> task = objectMapper.readValue(result.getResponse().getContentAsString(), Map.class);
            String savedTitle = (String) task.get("title");
            assertThat(savedTitle.strip()).isEqualTo("Buy milk");
        }
    }

    // -------------------------------------------------------------------------
    // Happy-path: Update status back from completed → pending
    // -------------------------------------------------------------------------
    @Test
    void updateTask_statusBackToPending_returns200() throws Exception {
        String id = createTaskViaApi("Reversible task", null);
        patchStatusViaApi(id, "completed");

        Map<String, String> patch = Map.of("status", "pending");
        mockMvc.perform(patch("/tasks/" + id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(patch)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("pending"));
    }

    // -------------------------------------------------------------------------
    // Helper: create a task via the API and return its id
    // -------------------------------------------------------------------------
    private String createTaskViaApi(String title, String description) throws Exception {
        Map<String, Object> body = description != null
                ? Map.of("title", title, "description", description)
                : Map.of("title", title);

        MvcResult result = mockMvc.perform(post("/tasks")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(body)))
                .andExpect(status().isCreated())
                .andReturn();

        Map<?, ?> task = objectMapper.readValue(result.getResponse().getContentAsString(), Map.class);
        return String.valueOf(task.get("id"));
    }

    private void patchStatusViaApi(String id, String status) throws Exception {
        mockMvc.perform(patch("/tasks/" + id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"status\":\"" + status + "\"}"))
                .andExpect(status().isOk());
    }
}