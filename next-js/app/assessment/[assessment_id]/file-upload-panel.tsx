"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Progress } from "@/components/ui/progress"
import { FileText, ImageIcon, File, Trash2, Upload, CheckCircle, AlertCircle, Loader2 } from "lucide-react"

interface UploadedFile {
  upload_id: string
  filename: string
  file_type: string
  file_size: number
  upload_status: "uploading" | "processing" | "completed" | "failed"
  ocr_status?: "pending" | "processing" | "completed" | "failed"
  upload_progress?: number
  created_at: string
}

interface FileUploadPanelProps {
  assessmentId: string
  onFileUploaded?: (file: UploadedFile) => void
}

export default function FileUploadPanel({ assessmentId, onFileUploaded }: FileUploadPanelProps) {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)

  // 업로드된 파일 목록 로드
  const fetchUploadedFiles = async () => {
    try {
      // 실제로는 GET /assessments/{assessment_id}/uploads API 호출
      // const response = await fetch(`/api/assessments/${assessmentId}/uploads`)
      // const data = await response.json()

      // 더미 데이터
      const dummyFiles: UploadedFile[] = [
        {
          upload_id: "upload_1",
          filename: "보험약관.pdf",
          file_type: "application/pdf",
          file_size: 2048576,
          upload_status: "completed",
          ocr_status: "completed",
          created_at: "2025-01-09T10:30:00Z",
        },
        {
          upload_id: "upload_2",
          filename: "진단서.jpg",
          file_type: "image/jpeg",
          file_size: 1024000,
          upload_status: "completed",
          ocr_status: "processing",
          created_at: "2025-01-09T10:35:00Z",
        },
      ]

      setUploadedFiles(dummyFiles)
    } catch (error) {
      console.error("파일 목록 로드 실패:", error)
    }
  }

  useEffect(() => {
    fetchUploadedFiles()
  }, [assessmentId])

  // 파일 아이콘 반환
  const getFileIcon = (fileType: string) => {
    if (fileType.startsWith("image/")) {
      return <ImageIcon className="h-4 w-4" />
    } else if (fileType === "application/pdf") {
      return <FileText className="h-4 w-4 text-red-500" />
    } else {
      return <File className="h-4 w-4" />
    }
  }

  // 파일 크기 포맷
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes"
    const k = 1024
    const sizes = ["Bytes", "KB", "MB", "GB"]
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i]
  }

  // 파일 업로드 처리
  const handleFileUpload = async (files: FileList) => {
    if (!files || files.length === 0) return

    setIsUploading(true)

    try {
      const formData = new FormData()
      Array.from(files).forEach((file) => {
        formData.append("files", file)
      })

      // 실제로는 POST /assessments/{assessment_id}/uploads API 호출
      // const response = await fetch(`/api/assessments/${assessmentId}/uploads`, {
      //   method: 'POST',
      //   body: formData
      // })
      // const data = await response.json()

      // 더미 업로드 시뮬레이션
      for (let i = 0; i < files.length; i++) {
        const file = files[i]
        const newFile: UploadedFile = {
          upload_id: `upload_${Date.now()}_${i}`,
          filename: file.name,
          file_type: file.type,
          file_size: file.size,
          upload_status: "uploading",
          upload_progress: 0,
          created_at: new Date().toISOString(),
        }

        setUploadedFiles((prev) => [...prev, newFile])

        // 업로드 진행률 시뮬레이션
        for (let progress = 0; progress <= 100; progress += 20) {
          await new Promise((resolve) => setTimeout(resolve, 200))
          setUploadedFiles((prev) =>
            prev.map((f) => (f.upload_id === newFile.upload_id ? { ...f, upload_progress: progress } : f)),
          )
        }

        // 업로드 완료 후 OCR 처리 시작
        setUploadedFiles((prev) =>
          prev.map((f) =>
            f.upload_id === newFile.upload_id ? { ...f, upload_status: "completed", ocr_status: "processing" } : f,
          ),
        )

        // OCR 처리 시뮬레이션
        setTimeout(() => {
          setUploadedFiles((prev) =>
            prev.map((f) => (f.upload_id === newFile.upload_id ? { ...f, ocr_status: "completed" } : f)),
          )
          onFileUploaded?.(newFile)
        }, 2000)
      }
    } catch (error) {
      console.error("파일 업로드 실패:", error)
    } finally {
      setIsUploading(false)
    }
  }

  // 파일 삭제
  const handleDeleteFile = async (uploadId: string) => {
    try {
      // 실제로는 DELETE /assessments/{assessment_id}/uploads/{upload_id} API 호출
      // await fetch(`/api/assessments/${assessmentId}/uploads/${uploadId}`, {
      //   method: 'DELETE'
      // })

      setUploadedFiles((prev) => prev.filter((f) => f.upload_id !== uploadId))
    } catch (error) {
      console.error("파일 삭제 실패:", error)
    }
  }

  // 드래그 앤 드롭 처리
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const files = e.dataTransfer.files
    if (files) {
      handleFileUpload(files)
    }
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="text-lg flex items-center">
          <Upload className="h-5 w-5 mr-2" />
          첨부파일 ({uploadedFiles.length})
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 파일 업로드 영역 */}
        <div
          className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
            dragOver ? "border-orange-400 bg-orange-50" : "border-gray-300 hover:border-orange-400"
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <Upload className="h-8 w-8 text-gray-400 mx-auto mb-2" />
          <p className="text-sm text-gray-600 mb-2">파일을 드래그하여 업로드하거나 클릭하여 선택하세요</p>
          <input
            type="file"
            multiple
            onChange={(e) => e.target.files && handleFileUpload(e.target.files)}
            className="hidden"
            id="file-upload"
            accept=".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png"
          />
          <Button
            variant="outline"
            onClick={() => document.getElementById("file-upload")?.click()}
            disabled={isUploading}
            className="text-sm"
          >
            {isUploading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                업로드 중...
              </>
            ) : (
              <>
                <Upload className="h-4 w-4 mr-2" />
                파일 선택
              </>
            )}
          </Button>
          <p className="text-xs text-gray-500 mt-2">지원 형식: PDF, DOC, DOCX, TXT, JPG, JPEG, PNG (최대 10MB)</p>
        </div>

        {/* 업로드된 파일 목록 */}
        {uploadedFiles.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-3">업로드된 파일</h4>
            <ScrollArea className="h-64">
              <div className="space-y-2">
                {uploadedFiles.map((file) => (
                  <div key={file.upload_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center space-x-3 flex-1 min-w-0">
                      <div className="flex-shrink-0">{getFileIcon(file.file_type)}</div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{file.filename}</p>
                        <div className="flex items-center space-x-2 text-xs text-gray-500">
                          <span>{formatFileSize(file.file_size)}</span>
                          <span>•</span>
                          <div className="flex items-center space-x-1">
                            {file.upload_status === "uploading" && (
                              <>
                                <Loader2 className="h-3 w-3 animate-spin" />
                                <span>업로드 중...</span>
                              </>
                            )}
                            {file.upload_status === "completed" && file.ocr_status === "processing" && (
                              <>
                                <Loader2 className="h-3 w-3 animate-spin text-blue-500" />
                                <span className="text-blue-600">OCR 처리 중</span>
                              </>
                            )}
                            {file.upload_status === "completed" && file.ocr_status === "completed" && (
                              <>
                                <CheckCircle className="h-3 w-3 text-green-500" />
                                <span className="text-green-600">처리 완료</span>
                              </>
                            )}
                            {file.upload_status === "failed" && (
                              <>
                                <AlertCircle className="h-3 w-3 text-red-500" />
                                <span className="text-red-600">업로드 실패</span>
                              </>
                            )}
                          </div>
                        </div>
                        {file.upload_status === "uploading" && file.upload_progress !== undefined && (
                          <Progress value={file.upload_progress} className="mt-1 h-1" />
                        )}
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDeleteFile(file.upload_id)}
                      className="flex-shrink-0 text-gray-400 hover:text-red-500"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
