# 09. Первый запуск AURORA MVP

## Что нужно

Python 3.11 или новее. Дополнительные библиотеки не требуются.

## Начало работы

В PowerShell в папке проекта выполните:

```powershell
.\tools\start.ps1
```

Создайте заметку:

```powershell
.\tools\aurora.ps1 note-add dmitry dmitry 'Идея для AURORA'
```

Создайте и завершите задачу:

```powershell
.\tools\aurora.ps1 task-add dmitry dmitry 'Проверить первую версию'
.\tools\aurora.ps1 task-list dmitry dmitry
.\tools\aurora.ps1 task-status dmitry <идентификатор-задачи> done
```

## Безопасность

Все данные остаются локально в `data/aurora.json`. Личная и семейная области не смешиваются. Для создания отдельной резервной копии используйте:

```powershell
.\tools\backup.ps1 -Actor dmitry -Space dmitry
```

## Проверка системы

```powershell
.\tools\verify.ps1
```
