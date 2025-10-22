# Video Chain Analyzer - Database Design

## Overview
This database schema supports advanced video analysis, frame-based matching, character/face recognition, and flexible chain creation across a large video collection.

## Database Tables

### 1. `videos`
Stores core video metadata and file information.

```sql
CREATE TABLE videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    original_path TEXT NOT NULL,
    normalized_path TEXT,  -- New flat structure path (e.g., "videos/video_00001.mp4")
    file_hash VARCHAR(64),  -- MD5/SHA256 of file for deduplication
    duration_seconds DECIMAL(10, 3),
    width INTEGER,
    height INTEGER,
    fps DECIMAL(10, 3),
    codec VARCHAR(50),
    file_size_bytes BIGINT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB  -- Flexible field for additional data (source, tags, etc.)
);

CREATE INDEX idx_videos_filename ON videos(filename);
CREATE INDEX idx_videos_file_hash ON videos(file_hash);
CREATE INDEX idx_videos_metadata ON videos USING GIN(metadata);
```

### 2. `frames`
Stores extracted frames with perceptual hashes at various timestamps.

```sql
CREATE TABLE frames (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    timestamp_seconds DECIMAL(10, 3) NOT NULL,  -- Position in video
    frame_type VARCHAR(20) NOT NULL,  -- 'first', 'last', 'middle', 'custom', 'keyframe'
    perceptual_hash VARCHAR(64) NOT NULL,  -- Average hash (16x16)
    dhash VARCHAR(64),  -- Difference hash (alternative)
    image_path TEXT,  -- Optional: path to saved frame image
    extracted_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_video_timestamp UNIQUE(video_id, timestamp_seconds)
);

CREATE INDEX idx_frames_video ON frames(video_id);
CREATE INDEX idx_frames_phash ON frames(perceptual_hash);
CREATE INDEX idx_frames_type ON frames(frame_type);
CREATE INDEX idx_frames_timestamp ON frames(timestamp_seconds);
```

### 3. `characters`
Stores detected faces/characters with embeddings for recognition.

```sql
CREATE TABLE characters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255),  -- User-assigned name (optional)
    face_embedding VECTOR(128),  -- Face recognition embedding (128D or 512D)
    first_seen_video_id UUID REFERENCES videos(id),
    appearance_count INTEGER DEFAULT 1,
    thumbnail_path TEXT,  -- Representative face image
    created_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB  -- Additional info (age estimation, gender, etc.)
);

CREATE INDEX idx_characters_name ON characters(name);
```

### 4. `video_characters`
Many-to-many relationship: which characters appear in which videos.

```sql
CREATE TABLE video_characters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    character_id UUID NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    confidence DECIMAL(5, 4),  -- Detection confidence (0.0 - 1.0)
    first_appearance_seconds DECIMAL(10, 3),  -- When they first appear
    last_appearance_seconds DECIMAL(10, 3),  -- When they last appear
    screen_time_seconds DECIMAL(10, 3),  -- Total time visible
    bounding_boxes JSONB,  -- Array of [{timestamp, x, y, w, h}, ...]

    CONSTRAINT unique_video_character UNIQUE(video_id, character_id)
);

CREATE INDEX idx_vc_video ON video_characters(video_id);
CREATE INDEX idx_vc_character ON video_characters(character_id);
CREATE INDEX idx_vc_confidence ON video_characters(confidence);
```

### 5. `chains`
User-created or auto-detected video chains.

```sql
CREATE TABLE chains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255),
    description TEXT,
    chain_type VARCHAR(50) NOT NULL,  -- 'auto_frame_match', 'manual', 'character_based', 'theme_based'
    created_by VARCHAR(50),  -- User identifier
    match_threshold INTEGER,  -- Hamming distance used (if auto-generated)
    total_videos INTEGER,
    total_duration_seconds DECIMAL(10, 3),
    created_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX idx_chains_type ON chains(chain_type);
CREATE INDEX idx_chains_created_at ON chains(created_at);
```

### 6. `chain_videos`
Ordered list of videos in each chain.

```sql
CREATE TABLE chain_videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chain_id UUID NOT NULL REFERENCES chains(id) ON DELETE CASCADE,
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    sequence_order INTEGER NOT NULL,  -- Position in chain (1, 2, 3...)
    transition_frame_id UUID REFERENCES frames(id),  -- Frame used for matching
    match_score DECIMAL(5, 4),  -- Similarity score with previous video
    trim_start_seconds DECIMAL(10, 3),  -- Optional: trim this much from start
    trim_end_seconds DECIMAL(10, 3),  -- Optional: trim this much from end

    CONSTRAINT unique_chain_video_order UNIQUE(chain_id, sequence_order)
);

CREATE INDEX idx_cv_chain ON chain_videos(chain_id, sequence_order);
CREATE INDEX idx_cv_video ON chain_videos(video_id);
```

### 7. `frame_matches`
Pre-computed frame similarity matches (for performance).

```sql
CREATE TABLE frame_matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    frame1_id UUID NOT NULL REFERENCES frames(id) ON DELETE CASCADE,
    frame2_id UUID NOT NULL REFERENCES frames(id) ON DELETE CASCADE,
    hamming_distance INTEGER NOT NULL,
    similarity_score DECIMAL(5, 4),  -- Normalized 0.0 - 1.0
    match_type VARCHAR(50),  -- 'first_to_last', 'middle_to_first', etc.
    computed_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_frame_pair UNIQUE(frame1_id, frame2_id)
);

CREATE INDEX idx_fm_distance ON frame_matches(hamming_distance);
CREATE INDEX idx_fm_score ON frame_matches(similarity_score DESC);
CREATE INDEX idx_fm_type ON frame_matches(match_type);
```

### 8. `tags`
Flexible tagging system for videos.

```sql
CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(50),  -- 'genre', 'mood', 'location', 'custom'
    color VARCHAR(7),  -- Hex color for UI
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_tags_category ON tags(category);
```

### 9. `video_tags`
Many-to-many: videos to tags.

```sql
CREATE TABLE video_tags (
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    added_at TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (video_id, tag_id)
);

CREATE INDEX idx_vt_tag ON video_tags(tag_id);
```

## Key Features

### 1. Multi-Frame Analysis
- Extract frames at any timestamp: `0s`, `2s`, `4s`, `duration-0.1s`, etc.
- Store multiple hash types (phash, dhash) for different matching strategies
- Support for keyframe detection

### 2. Character Tracking
- Face detection and recognition across all videos
- Track character appearances and screen time
- Build character-based chains (all videos featuring Character A)
- Face clustering for unnamed characters

### 3. Flexible Chain Creation
- **Auto Frame Match**: Traditional first→last frame matching
- **Character Based**: Chain videos featuring specific characters
- **Manual**: User-curated chains
- **Theme Based**: Chain by tags, mood, location

### 4. Performance Optimizations
- `frame_matches` table pre-computes expensive similarity calculations
- Indexes on all foreign keys and frequently queried fields
- JSONB for flexible metadata without schema changes
- Vector search for face embeddings (using pgvector extension)

### 5. Scalability
- UUID primary keys for distributed systems
- Partitioning potential on `created_at` for time-series data
- Normalized design prevents data duplication
- JSONB allows schema evolution without migrations

## Sample Queries

### Find all chains containing a specific video
```sql
SELECT c.*, cv.sequence_order
FROM chains c
JOIN chain_videos cv ON c.id = cv.chain_id
WHERE cv.video_id = 'video-uuid';
```

### Find similar frames across all videos
```sql
SELECT v1.filename, v2.filename, fm.hamming_distance
FROM frame_matches fm
JOIN frames f1 ON fm.frame1_id = f1.id
JOIN frames f2 ON fm.frame2_id = f2.id
JOIN videos v1 ON f1.video_id = v1.id
JOIN videos v2 ON f2.video_id = v2.id
WHERE fm.hamming_distance <= 10
ORDER BY fm.hamming_distance ASC
LIMIT 100;
```

### Find all videos with Character X
```sql
SELECT v.*, vc.confidence, vc.screen_time_seconds
FROM videos v
JOIN video_characters vc ON v.id = vc.video_id
WHERE vc.character_id = 'character-uuid'
ORDER BY vc.screen_time_seconds DESC;
```

### Build character-based chain
```sql
SELECT v.*, cv.sequence_order
FROM videos v
JOIN chain_videos cv ON v.id = cv.video_id
JOIN chains c ON cv.chain_id = c.id
WHERE c.chain_type = 'character_based'
  AND c.metadata->>'character_id' = 'character-uuid'
ORDER BY cv.sequence_order;
```

## Future Enhancements

1. **ML Features**
   - Scene detection and classification
   - Audio transcription and search
   - Object detection in frames
   - Mood/emotion analysis

2. **Advanced Analysis**
   - Video similarity beyond frame matching (optical flow, feature vectors)
   - Temporal pattern detection
   - Anomaly detection in chains

3. **Collaboration**
   - User accounts and permissions
   - Shared chains and annotations
   - Version control for chain edits

4. **Export/Integration**
   - Export chains as playlists
   - API for external tools
   - Integration with video editors (DaVinci Resolve, Premiere)

## Technology Stack Recommendation

- **Database**: PostgreSQL 16+ (for JSONB, Vector, and advanced indexes)
- **Extensions**:
  - `pgvector` - for face embedding similarity search
  - `pg_trgm` - for fuzzy text search on tags/names
- **ORM**: SQLAlchemy 2.0 (Python) or Prisma (TypeScript)
- **Caching**: Redis for frame_matches hot queries
- **Search**: Elasticsearch for metadata full-text search (optional)

## Migration Strategy

1. **Phase 1**: Core tables (videos, frames, chains, chain_videos)
2. **Phase 2**: Character recognition (characters, video_characters)
3. **Phase 3**: Performance optimization (frame_matches, indexes)
4. **Phase 4**: Tagging and metadata (tags, video_tags)

Each phase can be deployed independently without breaking existing functionality.
