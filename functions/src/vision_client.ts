import { ImageAnnotatorClient } from "@google-cloud/vision";

// Cloud Functions 런타임의 기본 서비스 계정(ADC)으로 인증한다.
// 별도 API 키를 발급/관리할 필요가 없는 대신, GCP 콘솔에서 Cloud Vision API를
// 활성화(enable)해 두어야 한다: https://console.cloud.google.com/apis/library/vision.googleapis.com
export const visionClient = new ImageAnnotatorClient();
