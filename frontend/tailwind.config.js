/** @type {import('tailwindcss').Config} */
// 顾客端 H5 设计令牌：光影画廊风格（规范详见 docs/设计规范.md）
export default {
  // 顾客端与管理端共用 Tailwind（管理端少量布局类使用）
  content: ['./index.html', './admin/index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      colors: {
        // 品牌深海蓝：主按钮、强调、激活态
        sea: {
          DEFAULT: '#17324F',
          deep: '#0F2438',
          soft: '#EEF2F6'
        },
        // 文字三级层级
        ink: {
          DEFAULT: '#1A2330',
          secondary: '#5A6572',
          faint: '#98A1AC'
        },
        hairline: '#E5E7EB', // 发丝分割线
        mist: '#F5F7F9' // 浅灰区块底（图片占位、底衬）
      },
      fontFamily: {
        // 中文系统字体栈：iOS 苹方 / 鸿蒙 / 小米 / Windows 雅黑兜底
        sans: ['-apple-system', 'BlinkMacSystemFont', '"PingFang SC"', '"HarmonyOS Sans SC"', '"MiSans"', '"Microsoft YaHei"', 'sans-serif']
      }
    }
  },
  plugins: []
}
