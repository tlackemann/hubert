import config from 'config'
import bunyan from 'bunyan'

class Log {
  constructor(app) {
    return bunyan.createLogger({
      name: app,
      stream: process.stdout,
      level: config.log.level,
    })
  }
}
const log = new Log('hue-app')
export default log
