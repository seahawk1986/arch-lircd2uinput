# This is an example PKGBUILD file. Use this as a start to creating your own,
# and remove these comments. For more information, see 'man PKGBUILD'.
# NOTE: Please fill out the license field for your package! If it is unknown,
# then please put 'unknown'.

# Maintainer: Alexander Grothe <sehawk1986@hotmail[dot]com>
pkgname=lircd2uinput
pkgver=0.0.1
pkgrel=1
epoch=
pkgdesc="create uinput events from lirc socket"
arch=('x86_64')
url=""
license=('GPL2')
groups=()
depends=('python2-gobject2' 'python2-uinput')
makedepends=()
checkdepends=()
optdepends=()
provides=('$pkgname')
conflicts=()
replaces=()
backup=()
options=()
install=
changelog=
source=($pkgname-$pkgver.tgz
       lircd2uinput.service)
noextract=()
md5sums=('1eca7b6311c9482e3f2152f5491a9394'
         '2b106f101338de61e9abbe7ca678a051')

package() {
  cd "$srcdir/$pkgname-$pkgver"
  install -Dm755 lircd2uinput.py "$pkgdir/usr/bin/lircd2uinput"
  install -D -m644 "${srcdir}"/lircd2uinput.service "${pkgdir}"/usr/lib/systemd/system/lircd2uinput.service
}

# vim:set ts=2 sw=2 et:
