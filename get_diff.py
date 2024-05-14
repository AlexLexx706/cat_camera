import cv2

class Diff:
    def __init__(self) -> None:
        self.backSub = cv2.createBackgroundSubtractorMOG2()

    def process(self, frame):
            # Apply background subtraction
            fg_mask = self.backSub.apply(frame)

            # apply global threshol to remove shadows
            __, mask_thresh = cv2.threshold(
                fg_mask, 140, 255, cv2.THRESH_BINARY)

            # set the kernal
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

            # Apply erosion
            mask_eroded = cv2.morphologyEx(mask_thresh, cv2.MORPH_OPEN, kernel)

            # Find contours
            contours, hierarchy = cv2.findContours(
                mask_eroded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            min_contour_area = 10  # Define your minimum area threshold
            large_contours = [
                cnt for cnt in contours if cv2.contourArea(cnt) > min_contour_area]

            cv2.drawContours(frame, large_contours, -1, (0, 255, 0), 2)
            frame_out = frame.copy()
            for cnt in large_contours:
                # print(cnt.shape)
                x, y, w, h = cv2.boundingRect(cnt)
                cv2.rectangle(
                    frame, (x, y), (x+w, y+h), (0, 0, 200), 3)
