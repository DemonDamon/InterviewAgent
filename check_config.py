from config.settings import settings

print("=== 火山引擎配置检查 ===")
print(f"APP_ID: {'已设置' if settings.volc_app_id else '❌ 未设置'}")
print(f"ACCESS_KEY: {'已设置' if settings.volc_access_key else '❌ 未设置'}")
print(f"RESOURCE_ID: {settings.volc_resource_id}")
print(f"APP_KEY: {settings.volc_app_key}")

if not settings.volc_app_id or not settings.volc_access_key:
    print("\n❌ 缺少必需的配置项！")
    print("请在 .env 文件中设置：")
    print("VOLC_APP_ID=your_app_id")
    print("VOLC_ACCESS_KEY=your_access_key")
else:
    print("\n✅ 配置完整") 