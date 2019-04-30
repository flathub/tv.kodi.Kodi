
## Kodi flatpak build notes.

The following binary plugins do not compile, and are excluded:

 * `audiodecoder.2sf`:
   - i386 compile issues
 * `audiodecoder.usf`:
   - i386 compile issues
 * `audiodecoder.sidplay`:
   - sidplay-libs does not compile. Is code from 2006 - bitrot.
 * `pvr.iptvsimple`:
   - requires rapidxml, which is only headers

Others need try/testing:
 - `game.libretro.2048`
 - `game.libretro.mrboom`
 - `imagedecoder.mpo`
 - `imagedecoder.raw`
 - `pvr.dvblink`
 - `pvr.hdhomerun`
 - `screensaver.asterwave`
 - `screensaver.cpblobs`
 - `screensaver.matrixtrails`
 - `screensavers.rsxs`
 - `vfs.libarchive`
 - `vfs.sftp`
 - `visualization.goom`
 - `visualization.projectm`
