# 本地主题登记行
#
# 每行一个主题，格式与 vendor/gzh-design/references/theme-index.md 的表格行完全一致：
# | 主题 | 主色 | 适用场景 | 组件库文件 | 正文下划线 CSS |
#
# 主题组件库文件放在本目录，命名 theme-{英文标识}.md，
# 同步脚本会自动拷贝到 vendor/gzh-design/references/ 并在此登记。
#
# 新增主题流程：
# 1. 按 vendor/gzh-design/references/theme-generator.md 生成主题组件库
# 2. 把生成的 theme-{英文标识}.md 放到本目录（4_theme-formator/themes-local/）
# 3. 在下方登记一行，跑 python3 4_theme-formator/scripts/inject-local-themes.py 验证
#
# 示例（取消注释即可启用）：
# | 我的品牌 | `#3B82F6` blue | 品牌内容、产品发布 | `references/theme-my-brand.md` | `border-bottom:2px solid #BFDBFE;font-weight:600;` |
