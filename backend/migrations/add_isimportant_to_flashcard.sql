-- Add the missing Boolean column with a safe default
ALTER TABLE flashcards
ADD COLUMN isImportant BOOLEAN NOT NULL DEFAULT 0;