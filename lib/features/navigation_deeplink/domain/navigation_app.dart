/// 길안내에 사용할 수 있는 내비게이션 앱.
enum NavigationApp {
  kakaoNavi('카카오내비'),
  tmap('T맵'),
  naverMap('네이버지도');

  const NavigationApp(this.label);

  final String label;
}
