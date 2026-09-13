import * as admin from "firebase-admin";

// App Check 토큰 검증(admin.appCheck())을 쓰려면 Admin SDK가 초기화되어 있어야 한다.
// Cloud Functions 런타임에서는 인자 없이 호출하면 기본 서비스 계정을 사용한다.
if (admin.apps.length === 0) {
  admin.initializeApp();
}

export { admin };
