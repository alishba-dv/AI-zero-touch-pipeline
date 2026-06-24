package com.example.app;

import java.util.List;
import java.util.Optional;

public interface TaskRepository {
    Task save(Task task);
    List<Task> findAll();
    Optional<Task> findById(String id);
    boolean deleteById(String id);
    void deleteAll();
}