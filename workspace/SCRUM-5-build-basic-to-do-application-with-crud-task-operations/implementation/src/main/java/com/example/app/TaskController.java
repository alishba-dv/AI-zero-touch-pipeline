package com.example.app;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Pattern;

@RestController
@RequestMapping("/tasks")
public class TaskController {

    // Allows alphanumeric characters, hyphens, and underscores — rejects special chars like '!'
    private static final Pattern VALID_ID_PATTERN = Pattern.compile("[a-zA-Z0-9_-]+");
    private static final Set<String> VALID_STATUSES = Set.of("pending", "completed");

    private final TaskRepository taskRepository;

    public TaskController(TaskRepository taskRepository) {
        this.taskRepository = taskRepository;
    }

    @PostMapping
    public ResponseEntity<?> createTask(@RequestBody CreateTaskRequest request) {
        if (request.getTitle() == null) {
            return badRequest("Title is required");
        }
        String title = request.getTitle().trim();
        if (title.isEmpty()) {
            return badRequest("Title must not be blank");
        }

        Task task = new Task();
        task.setId(UUID.randomUUID().toString());
        task.setTitle(title);
        task.setDescription(request.getDescription());
        task.setStatus("pending");
        task.setCreatedAt(Instant.now().toString());

        taskRepository.save(task);
        return ResponseEntity.status(HttpStatus.CREATED).body(task);
    }

    @GetMapping
    public ResponseEntity<List<Task>> listTasks() {
        return ResponseEntity.ok(taskRepository.findAll());
    }

    @PatchMapping("/{id}")
    public ResponseEntity<?> updateTask(@PathVariable String id,
                                        @RequestBody UpdateTaskRequest request) {
        if (!isValidId(id)) {
            return badRequest("Invalid task ID format");
        }
        if (!request.hasAnyField()) {
            return badRequest("At least one field must be provided for update");
        }
        if (request.getStatus() != null && !VALID_STATUSES.contains(request.getStatus())) {
            return badRequest("Status must be 'pending' or 'completed'");
        }

        Optional<Task> found = taskRepository.findById(id);
        if (found.isEmpty()) {
            return notFound("Task not found: " + id);
        }

        Task task = found.get();
        if (request.getTitle() != null) {
            task.setTitle(request.getTitle());
        }
        if (request.getDescription() != null) {
            task.setDescription(request.getDescription());
        }
        if (request.getStatus() != null) {
            task.setStatus(request.getStatus());
        }
        taskRepository.save(task);
        return ResponseEntity.ok(task);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<?> deleteTask(@PathVariable String id) {
        if (!isValidId(id)) {
            return badRequest("Invalid task ID format");
        }
        if (!taskRepository.deleteById(id)) {
            return notFound("Task not found: " + id);
        }
        return ResponseEntity.noContent().build();
    }

    private boolean isValidId(String id) {
        return VALID_ID_PATTERN.matcher(id).matches();
    }

    private ResponseEntity<ErrorResponse> badRequest(String message) {
        return ResponseEntity.badRequest().body(new ErrorResponse(message));
    }

    private ResponseEntity<ErrorResponse> notFound(String message) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(new ErrorResponse(message));
    }
}