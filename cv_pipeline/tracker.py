import numpy as np

class Track:
    def __init__(self, track_id, bbox, centroid, gender=None, age=None):
        self.track_id = track_id
        self.bbox = bbox  # [x, y, w, h]
        self.centroid = centroid  # (cx, cy)
        self.history = [centroid]  # list of points
        self.disappeared_count = 0
        self.gender = gender
        self.age = age
        
        # Demographic profile stabilization (keep running majority/mean)
        self.gender_votes = [gender] if gender else []
        self.age_votes = [age] if age else []

    def update(self, bbox, centroid, gender=None, age=None):
        self.bbox = bbox
        self.centroid = centroid
        self.history.append(centroid)
        self.disappeared_count = 0
        if gender:
            self.gender_votes.append(gender)
        if age:
            self.age_votes.append(age)

    @property
    def final_gender(self):
        if not self.gender_votes:
            return "F"  # default
        # Return majority vote
        return max(set(self.gender_votes), key=self.gender_votes.count)

    @property
    def final_age(self):
        if not self.age_votes:
            return 28  # default
        return int(np.mean(self.age_votes))

class CentroidTracker:
    def __init__(self, max_disappeared=10, max_distance=150):
        self.next_track_id = 101
        self.tracks = {}  # track_id -> Track object
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance

    def _calculate_iou(self, boxA, boxB):
        # Determine the coordinates of the intersection rectangle
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[0] + boxA[2], boxB[0] + boxB[2])
        yB = min(boxA[1] + boxA[3], boxB[1] + boxB[3])

        # Compute the area of intersection
        interArea = max(0, xB - xA) * max(0, yB - yA)
        if interArea == 0:
            return 0.0

        # Compute the area of both bounding boxes
        boxAArea = boxA[2] * boxA[3]
        boxBArea = boxB[2] * boxB[3]

        # Compute the union
        iou = interArea / float(boxAArea + boxBArea - interArea)
        return iou

    def register(self, bbox, centroid, gender=None, age=None):
        track = Track(self.next_track_id, bbox, centroid, gender, age)
        self.tracks[self.next_track_id] = track
        self.next_track_id += 1
        return track.track_id

    def deregister(self, track_id):
        if track_id in self.tracks:
            del self.tracks[track_id]

    def update(self, rects, genders=None, ages=None):
        """
        Updates the tracker with new detections.
        rects: list of bounding boxes [x, y, w, h]
        """
        if genders is None:
            genders = [None] * len(rects)
        if ages is None:
            ages = [None] * len(rects)

        # If no detections, increment disappeared count of all active tracks
        if len(rects) == 0:
            for track_id in list(self.tracks.keys()):
                self.tracks[track_id].disappeared_count += 1
                if self.tracks[track_id].disappeared_count > self.max_disappeared:
                    self.deregister(track_id)
            return self.tracks

        # Compute centroids of new detections
        input_centroids = np.zeros((len(rects), 2), dtype="int")
        for i, (x, y, w, h) in enumerate(rects):
            cx = int(x + w / 2.0)
            cy = int(y + h / 2.0)
            input_centroids[i] = (cx, cy)

        # If we have no active tracks, register all detections
        if len(self.tracks) == 0:
            for i in range(len(rects)):
                self.register(rects[i], tuple(input_centroids[i]), genders[i], ages[i])
            return self.tracks

        # Grab matching candidates
        track_ids = list(self.tracks.keys())
        track_centroids = np.array([self.tracks[tid].centroid for tid in track_ids])

        # Compute distances between active track centroids and input centroids
        D = np.linalg.norm(track_centroids[:, np.newaxis] - input_centroids, axis=2)

        # Find row (track) and col (detection) indices that minimize distance
        rows = D.min(axis=1).argsort()
        cols = D.argmin(axis=1)[rows]

        used_rows = set()
        used_cols = set()

        for row, col in zip(rows, cols):
            if row in used_rows or col in used_cols:
                continue

            # Check if distance exceeds threshold
            if D[row, col] > self.max_distance:
                continue

            track_id = track_ids[row]
            self.tracks[track_id].update(
                rects[col], 
                tuple(input_centroids[col]), 
                genders[col], 
                ages[col]
            )
            used_rows.add(row)
            used_cols.add(col)

        # Unmatched active tracks
        unused_rows = set(range(D.shape[0])).difference(used_rows)
        for row in unused_rows:
            track_id = track_ids[row]
            self.tracks[track_id].disappeared_count += 1
            if self.tracks[track_id].disappeared_count > self.max_disappeared:
                self.deregister(track_id)

        # Unmatched input detections -> register as new tracks
        unused_cols = set(range(D.shape[1])).difference(used_cols)
        for col in unused_cols:
            self.register(rects[col], tuple(input_centroids[col]), genders[col], ages[col])

        return self.tracks
